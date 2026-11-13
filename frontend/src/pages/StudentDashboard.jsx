import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../AuthContext';
import Navbar from '../components/Navbar';
import PageHeader from '../components/common/PageHeader';
import PreExamAuth from '../components/PreExamAuth'; 
import Webcam from "react-webcam"; 
import '../styles/StudentDashboard.css'; 
import { decryptText, hashText } from '../utils/encryption'; //  IMPORT ENCRYPTION UTILS
import { FileText, Lock, Clock, Calendar, AlertCircle, AlertTriangle } from 'lucide-react';

const StudentDashboard = () => {
  const { user, API_BASE_URL, getHeaders } = useAuth();
  
  // -- STATE --
  const [loading, setLoading] = useState(true);
  const [exams, setExams] = useState([]);
  const [activeExam, setActiveExam] = useState(null);
  const [now, setNow] = useState(new Date()); 
  
  //  PHASE 3: AUTH STATE
  const [authStep, setAuthStep] = useState('list'); 
  const [capturedImages, setCapturedImages] = useState({ id: null, face: null });

  //  NEW: PASSWORD STATE
  const [showPasswordPrompt, setShowPasswordPrompt] = useState(false);
  const [examPassword, setExamPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  
  // ℹ️ NEW: EXAM DETAILS STATE
  const [examDetails, setExamDetails] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  
  //  NEW: EXAM REVIEW STATE
  const [reviewData, setReviewData] = useState(null);

  //  NEW: SECRET CAPTURE STATE
  const [secretMidExamPhoto, setSecretMidExamPhoto] = useState(null);
  const hasCapturedSecretRef = useRef(false);

  // ️ NEW: FULL SCREEN STATE
  const [isFullscreen, setIsFullscreen] = useState(false);
  const hasEnteredFullScreenRef = useRef(false);

  // Quiz State
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({}); 
  const [currentQIndex, setCurrentQIndex] = useState(0); 
  const [visited, setVisited] = useState({}); 
  const [timeLeft, setTimeLeft] = useState(0); 
  
  const [viewMode, setViewMode] = useState('single'); 
  const [proctorStatus, setProctorStatus] = useState("safe");
  const [showAlert, setShowAlert] = useState(false);
  const questionRefs = useRef({});

  //  PHASE 2: ANTI-CHEATING STATE
  const [warnings, setWarnings] = useState(0);
  const [showCheatWarning, setShowCheatWarning] = useState(false);
  
  //  Separate Audio Warning State
  const [showAudioAlert, setShowAudioAlert] = useState(false);
  const lastAudioWarningTime = useRef(0);
  
  // ️ Silent Backend Trackers
  const audioWarningsRef = useRef(0); 
  const lastWarningTime = useRef(0); 
  const answersRef = useRef({}); 
  const micStreamRef = useRef(null); 
  
  //  FIX: Prevent Tab Switch Warning on Submit Dialog
  const isSubmittingRef = useRef(false);

  //  Reference to the exam webcam for silent screenshots
  const proctorWebcamRef = useRef(null);
  const faceMissingSinceRef = useRef(null); 
  
  const MAX_WARNINGS = 3;

  // Keep answersRef synced with answers state for auto-submit
  useEffect(() => { answersRef.current = answers; }, [answers]);

  // 0. Clock Tick
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);


  // --- ️ FULL SCREEN HANDLER ---
  const enterFullScreen = async () => {
      const elem = document.documentElement; // Make the entire page full screen
      try {
          if (elem.requestFullscreen) {
              await elem.requestFullscreen();
          } else if (elem.webkitRequestFullscreen) { /* Safari */
              await elem.webkitRequestFullscreen();
          } else if (elem.msRequestFullscreen) { /* IE11 */
              await elem.msRequestFullscreen();
          }
          hasEnteredFullScreenRef.current = true;
          setIsFullscreen(true);
      } catch (err) {
          console.error("Error attempting to enable full-screen mode:", err);
          alert("Your browser blocked full screen mode. Please allow it to continue.");
      }
  };


  // --- ️ AUDIO ANALYSIS LOGIC ---
  const startAudioAnalysis = (stream) => {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);
      
      analyser.smoothingTimeConstant = 0.8;
      analyser.fftSize = 256;
      microphone.connect(analyser);
      
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      
      const checkAudioLevel = () => {
          if (!micStreamRef.current) return; 
          
          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
          let averageVolume = sum / dataArray.length;

          if (averageVolume > 45) { 
              const currentTime = Date.now();
              if (currentTime - lastAudioWarningTime.current > 4000) {
                  lastAudioWarningTime.current = currentTime;
                  setShowAudioAlert(true);
                  
                  if (audioWarningsRef.current < 5) {
                      audioWarningsRef.current += 1;
                      
                      const saved = sessionStorage.getItem('examSession');
                      if (saved) {
                          const session = JSON.parse(saved);
                          session.audioWarnings = audioWarningsRef.current;
                          sessionStorage.setItem('examSession', JSON.stringify(session));

                          // Explicitly log the audio event using the attempt_id from the session
                          if (session.activeExam && session.activeExam.attempt_id) {
                              fetch(`${API_BASE_URL}/exams/proctoring_event`, {
                                  method: 'POST',
                                  headers: { ...getHeaders(), 'Content-Type': 'application/json' },
                                  body: JSON.stringify({
                                      attempt_id: session.activeExam.attempt_id,
                                      event_type: 'AUDIO_ACTIVITY',
                                      severity: 'LOW',
                                      duration_ms: 3000
                                  })
                              }).catch(e => console.error("Audio log fail", e));
                          }
                      }
                  }
                  
                  setTimeout(() => { setShowAudioAlert(false); }, 3000);
              }
          }
          requestAnimationFrame(checkAudioLevel);
      };
      checkAudioLevel();
  };


  // 1. Fetch Data &  RECOVER PREVIOUS EXAM SESSION
  useEffect(() => {
    const fetchData = async () => {
      try {
        const savedSession = sessionStorage.getItem('examSession');
        if (savedSession) {
            const session = JSON.parse(savedSession);
            const remainingTime = Math.floor((session.endTime - Date.now()) / 1000);

            if (remainingTime > 0) {
                setActiveExam(session.activeExam);
                setQuestions(session.questions);
                setAnswers(session.answers || {});
                setWarnings(session.warnings || 0);
                audioWarningsRef.current = session.audioWarnings || 0;
                setCapturedImages(session.capturedImages);
                setTimeLeft(remainingTime);
                setCurrentQIndex(session.currentQIndex || 0);
                setVisited(session.visited || { 0: true });

                if (session.secretMidExamPhoto) {
                    setSecretMidExamPhoto(session.secretMidExamPhoto);
                    hasCapturedSecretRef.current = true;
                }

                setAuthStep('exam'); 
                
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    micStreamRef.current = stream; 
                    startAudioAnalysis(stream);
                } catch (err) { console.warn("Mic denied on reload"); }
            } else {
                sessionStorage.removeItem('examSession'); 
            }
        }
        
        const examRes = await fetch(`${API_BASE_URL}/exams`, { headers: getHeaders() });
        if (examRes.status === 401) {
            localStorage.removeItem('user');
            localStorage.removeItem('token');
            window.location.href = '/login?expired=1';
            return;
        }
        const examsData = examRes.ok ? await examRes.json() : [];
        if (!Array.isArray(examsData)) {
            console.warn("Exams response is not an array:", examsData);
            setExams([]);
            return;
        }

        const attemptRes = await fetch(`${API_BASE_URL}/attempts/my_attempts`, { headers: getHeaders() });
        let attemptedIds = [];
        if (attemptRes.ok) {
            const rawAttempts = await attemptRes.json();
            if (Array.isArray(rawAttempts)) attemptedIds = rawAttempts;
        }

        const mergedExams = examsData.map(exam => ({
            ...exam,
            attempted: attemptedIds.includes(exam.id)
        }));

        setExams(mergedExams);
      } catch (e) { console.error(e); } finally { setLoading(false); }
    };
    fetchData();
  }, [API_BASE_URL]);


  // ---  PHASE 1: ENTER LOBBY & DETAILS PROMPT ---
  const handleSelectExam = async (exam) => {
    if (exam.assigned_slot) {
        const now = new Date();
        const start = new Date(exam.assigned_slot.start_time);
        const end = new Date(exam.assigned_slot.end_time);
        if (now < start) {
            alert(`Your exam slot starts at ${start.toLocaleString()}`);
            return;
        } else if (now > end) {
            alert(`Your exam slot has ended.`);
            return;
        }
    }
    
    setActiveExam(exam);
    try {
        const res = await fetch(`${API_BASE_URL}/exams/${exam.id}/details`, { headers: getHeaders() });
        if (res.ok) {
            setExamDetails(await res.json());
            setShowDetailsModal(true);
        }
    } catch (e) { console.error(e); }
  };

  const handleProceedToAuth = () => {
    setShowDetailsModal(false);
    if (activeExam.has_password) {
        setExamPassword('');
        setPasswordError('');
        setShowPasswordPrompt(true); 
    } else {
        setAuthStep('auth'); 
    }
  };

  const handlePasswordSubmit = async () => {
      if (!examPassword) return setPasswordError("Please enter a password.");
      try {
          const res = await fetch(`${API_BASE_URL}/exams/${activeExam.id}/verify_password`, {
              method: 'POST',
              headers: getHeaders(),
              body: JSON.stringify({ password: examPassword })
          });
          if (res.ok) {
              setShowPasswordPrompt(false);
              setAuthStep('auth'); 
          } else {
              const data = await res.json();
              setPasswordError(data.message || "Invalid password");
          }
      } catch (e) {
          setPasswordError("Connection error");
      }
  };


  // --- ️ PHASE 2: START EXAM ---
  const handleAuthSuccess = async (idImage, faceImage) => {
    setCapturedImages({ id: idImage, face: faceImage });

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        micStreamRef.current = stream; 
        startAudioAnalysis(stream);
    } catch (err) {
        alert(" Microphone access is required to take this proctored exam.");
        setAuthStep('list'); 
        return; 
    }

    try {
        // 1. Notify Backend that Attempt is starting (Enforces attempt count and timer)
        const startRes = await fetch(`${API_BASE_URL}/exams/${activeExam.id}/start`, {
            method: 'POST',
            headers: getHeaders()
        });
        
        if (!startRes.ok) {
            const errData = await startRes.json();
            alert(` Cannot start exam: ${errData.message}`);
            setAuthStep('list');
            return;
        }
        
        const startData = await startRes.json();
        const currentAttemptId = startData.attempt_id;

        // 2. Fetch Questions
        const res = await fetch(`${API_BASE_URL}/exams/${activeExam.id}/questions`, { headers: getHeaders() });
        if (res.ok) {
            const rawData = await res.json();
            
            //  DECRYPT EXAM HERE
            let decryptedQuestions = [];
            try {
                decryptedQuestions = rawData.map(q => ({
                    ...q,
                    text: activeExam.has_password ? decryptText(q.text, examPassword) : q.text,
                    options: {
                        A: activeExam.has_password ? decryptText(q.option_a, examPassword) : q.option_a,
                        B: activeExam.has_password ? decryptText(q.option_b, examPassword) : q.option_b,
                        C: activeExam.has_password ? decryptText(q.option_c, examPassword) : q.option_c,
                        D: activeExam.has_password ? decryptText(q.option_d, examPassword) : q.option_d,
                    }
                }));

                if (decryptedQuestions.length > 0 && decryptedQuestions[0].text && decryptedQuestions[0].text.includes("[Encrypted Data")) {
                    throw new Error("Invalid Password");
                }
            } catch (decryptionError) {
                alert(" Decryption Failed. The exam password you entered is incorrect.");
                setAuthStep('list'); 
                return;
            }

            setQuestions(decryptedQuestions);
            
            const durationSecs = activeExam.duration * 60;
            setTimeLeft(durationSecs); 
            setVisited({ 0: true }); 
            setCurrentQIndex(0);
            setWarnings(0); 
            audioWarningsRef.current = 0; 
            setShowCheatWarning(false);
            
            setSecretMidExamPhoto(null);
            hasCapturedSecretRef.current = false;

            sessionStorage.setItem('examSession', JSON.stringify({
                activeExam: { ...activeExam, attempt_id: currentAttemptId },
                questions: decryptedQuestions, 
                answers: {},
                warnings: 0,
                audioWarnings: 0,
                capturedImages: { id: idImage, face: faceImage },
                endTime: Date.now() + (durationSecs * 1000),
                currentQIndex: 0,
                visited: { 0: true }
            }));

            setAuthStep('exam'); 
        }
    } catch (e) { console.error(e); }
  };


  const logProctoringEvent = async (eventType, severity, durationMs = 0) => {
    if (!activeExam || !activeExam.attempt_id) return;
    try {
        await fetch(`${API_BASE_URL}/exams/proctoring_event`, {
            method: 'POST',
            headers: { ...getHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({
                attempt_id: activeExam.attempt_id,
                event_type: eventType,
                severity: severity,
                duration_ms: durationMs
            })
        });
    } catch (e) { console.error("Failed to log proctoring event", e); }
  };

  // ---  WARNING TRIGGER ---
  const triggerTabViolation = () => {
    //  FIX: If the user is actively submitting the exam (dialog is open), ignore the blur event!
    if (isSubmittingRef.current) return;

    logProctoringEvent('TAB_SWITCH', 'MEDIUM');

    const currentTime = Date.now();
    if (currentTime - lastWarningTime.current < 5000) return; 
    lastWarningTime.current = currentTime;

    setWarnings(prev => {
        const newCount = prev + 1;
        if (newCount >= MAX_WARNINGS) {
            submitExam(true); 
        } else {
            setShowCheatWarning(true); 
        }
        return newCount;
    });
  };

  // --- ️ TAB-SWITCH, FULL-SCREEN &  ANTI-COPY DETECTION ---
  useEffect(() => {
    if (authStep !== 'exam' || timeLeft <= 0) return;

    // 1. Tab Switch Handlers
    const handleVisibilityChange = () => { if (document.hidden) triggerTabViolation(); };
    const handleWindowBlur = () => { triggerTabViolation(); };

    //  2. NEW: Full Screen Tracker
    const handleFullScreenChange = () => {
        // If the submit dialog is open, do not penalize them for full screen changes
        if (isSubmittingRef.current) return; 

        const isFull = !!document.fullscreenElement || !!document.webkitFullscreenElement || !!document.msFullscreenElement;
        setIsFullscreen(isFull);
        
        // If they exit full screen AFTER successfully entering it, punish them
        if (!isFull && hasEnteredFullScreenRef.current) {
            triggerTabViolation();
        }
    };

    // 3. Anti-Copy Handlers
    const disableContextMenu = (e) => e.preventDefault(); 
    const disableCopyPaste = (e) => e.preventDefault(); 

    const disableKeyboardShortcuts = (e) => {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'C' || e.key === 'v' || e.key === 'V' || e.key === 'x' || e.key === 'X')) {
            e.preventDefault();
        }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleWindowBlur);
    
    // Add Full Screen Listeners (including Safari compatibility)
    document.addEventListener("fullscreenchange", handleFullScreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullScreenChange); 

    document.addEventListener("contextmenu", disableContextMenu);
    document.addEventListener("copy", disableCopyPaste);
    document.addEventListener("cut", disableCopyPaste);
    document.addEventListener("paste", disableCopyPaste);
    document.addEventListener("keydown", disableKeyboardShortcuts);

    return () => {
        document.removeEventListener("visibilitychange", handleVisibilityChange);
        window.removeEventListener("blur", handleWindowBlur);
        
        document.removeEventListener("fullscreenchange", handleFullScreenChange);
        document.removeEventListener("webkitfullscreenchange", handleFullScreenChange);
        
        document.removeEventListener("contextmenu", disableContextMenu);
        document.removeEventListener("copy", disableCopyPaste);
        document.removeEventListener("cut", disableCopyPaste);
        document.removeEventListener("paste", disableCopyPaste);
        document.removeEventListener("keydown", disableKeyboardShortcuts);
    };
  }, [authStep, timeLeft]); 


  // ---  PREVENT ACCIDENTAL REFRESH POPUP ---
  useEffect(() => {
    const handleBeforeUnload = (e) => {
        if (authStep === 'exam') {
            e.preventDefault();
            e.returnValue = "You have an active exam! Are you sure you want to reload? Progress might be lost.";
        }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [authStep]);


  // ---  AUTO-SAVE EVERY ACTION TO SESSION STORAGE ---
  useEffect(() => {
    if (authStep === 'exam') {
        const saved = sessionStorage.getItem('examSession');
        if (saved) {
            const session = JSON.parse(saved);
            session.answers = answers;
            session.warnings = warnings;
            session.currentQIndex = currentQIndex; 
            session.visited = visited;             
            sessionStorage.setItem('examSession', JSON.stringify(session));
        }
    }
  }, [answers, warnings, authStep, currentQIndex, visited]);


  // --- HELPER FORMATTERS ---
  const safeDate = (dateString) => {
    if (!dateString) return null;
    const d = new Date(dateString);
    return isNaN(d.getTime()) ? null : d;
  };

  const formatDateDisplay = (dateObj) => {
    if (!dateObj) return "N/A";
    return dateObj.toLocaleString([], {
        month: 'short', day: 'numeric', 
        hour: '2-digit', minute: '2-digit'
    });
  };

  const getExamTimes = (exam) => {
    const start = exam.assigned_slot ? new Date(exam.assigned_slot.start_time) : safeDate(exam.start_date);
    let end = exam.assigned_slot ? new Date(exam.assigned_slot.end_time) : safeDate(exam.end_date);
    if (!end && start && exam.duration) {
        end = new Date(start.getTime() + exam.duration * 60000);
    }
    return { start, end };
  };

  const getExamStatus = (exam) => {
    if (exam.attempted) return { label: "Completed", icon: "", color: "secondary", disabled: true, action: "review" };

    const { start, end } = getExamTimes(exam);

    if (!start || !end) return { label: "Start Exam", icon: "", color: "primary", disabled: false };

    if (now < start) {
        return { 
            label: `Starts: ${start.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`, 
            icon: "⏳",
            color: "warning", 
            disabled: true 
        };
    }
    
    if (now > end) {
        return { label: "Expired", icon: "", color: "danger", disabled: true };
    }
    
    return { label: "Start Exam", icon: "", color: "primary", disabled: false };
  };

  // ---  SUBMIT & CLEANUP ---
  const submitExam = async (force = false) => {
    //  FIX: Pause proctor tracking so the dialog box doesn't trigger a warning!
    isSubmittingRef.current = true; 

    if (!force && !window.confirm("Submit?")) {
        // If they click cancel, resume tracking
        isSubmittingRef.current = false; 
        return;
    }
    
    sessionStorage.removeItem('examSession');
    
    if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach(track => track.stop());
        micStreamRef.current = null;
    }

    // ️ EXIT FULL SCREEN UPON COMPLETION
    if (document.fullscreenElement) {
        document.exitFullscreen().catch(err => console.log(err));
    }

    //  E2E SECURITY: HASH ANSWERS BEFORE SUBMITTING
    const hashedAnswers = {};
    for (const [qId, selectedOption] of Object.entries(answersRef.current)) {
        const question = questions.find(q => q.id === parseInt(qId));
        if (question && question.is_subjective) {
            hashedAnswers[qId] = selectedOption; // Raw text for subjective
        } else {
            hashedAnswers[qId] = hashText(String(selectedOption).trim().toUpperCase()); 
        }
    }

    try {
        await fetch(`${API_BASE_URL}/exams/${activeExam.id}/submit`, {
            method: 'POST', 
            headers: getHeaders(), 
            body: JSON.stringify({ 
                answers: hashedAnswers, 
                tab_switches: warnings,                  
                audio_warnings: audioWarningsRef.current, 
                id_image: capturedImages.id,             
                face_image: capturedImages.face,
                mid_exam_photo: secretMidExamPhoto || capturedImages.face 
            })
        });
        if (force) alert(" Exam AUTO-SUBMITTED due to rule violations or time out.");
        window.location.reload(); 
    } catch (e) {}
  };

  // ---  FETCH EXAM REVIEW ---
  const handleReviewExam = async (exam) => {
      try {
          const res = await fetch(`${API_BASE_URL}/exams/${exam.id}/review`, { headers: getHeaders() });
          if (res.ok) {
              const data = await res.json();
              setReviewData({ ...data, examTitle: exam.title, examId: exam.id });
          } else {
              alert("Could not load review.");
          }
      } catch (e) {
          console.error(e);
      }
  };

  // --- 3. TIMER ---
  useEffect(() => {
    if (authStep !== 'exam' || timeLeft <= 0) return;
    const timer = setInterval(() => {
        setTimeLeft(prev => {
            if (prev <= 1) { clearInterval(timer); submitExam(true); return 0; } 
            return prev - 1;
        });
    }, 1000);
    return () => clearInterval(timer);
  }, [authStep, timeLeft]);

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec < 10 ? '0' : ''}${sec}`;
  };

  // ---  4. PROCTOR CHECK & SECRET PHOTO CAPTURE ---
  useEffect(() => {
    let interval;
    if (authStep === 'exam') {
      interval = setInterval(async () => {
        try {
          if (proctorWebcamRef.current) {
            const imageSrc = proctorWebcamRef.current.getScreenshot();
            if (imageSrc) {
              
              const headers = getHeaders();
              headers['Content-Type'] = 'application/json';

              const res = await fetch(`${API_BASE_URL}/exams/analyze_frame`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ 
                    frame: imageSrc, 
                    attempt_id: activeExam?.attempt_id 
                })
              });
              
              if (res.ok) {
                const data = await res.json();
                const currentStatus = data.status;

                if (!hasCapturedSecretRef.current) {
                    const sessionStr = sessionStorage.getItem('examSession');
                    if (sessionStr) {
                        const session = JSON.parse(sessionStr);
                        const examDurationMs = session.activeExam.duration * 60 * 1000;
                        const timeElapsed = examDurationMs - (session.endTime - Date.now());
                        
                        if (timeElapsed > 900000) {
                            setSecretMidExamPhoto(imageSrc);
                            hasCapturedSecretRef.current = true;
                            session.secretMidExamPhoto = imageSrc;
                            sessionStorage.setItem('examSession', JSON.stringify(session));
                        }
                    }
                }

                if (currentStatus === "missing") {
                    if (!faceMissingSinceRef.current) {
                        faceMissingSinceRef.current = Date.now();
                    } else if (Date.now() - faceMissingSinceRef.current >= 3000) { 
                        setProctorStatus("missing");
                        setShowAlert(true);
                    }
                } else {
                    faceMissingSinceRef.current = null; 
                    setProctorStatus(currentStatus);
                    setShowAlert(currentStatus !== "safe");
                }
              }
            }
          }
        } catch (e) { 
            console.error("Failed to send frame to backend", e); 
        }
      }, 2000); 
    }
    return () => clearInterval(interval);
  }, [authStep, API_BASE_URL]);

  const handleOptionSelect = (qId, opt) => setAnswers(prev => ({ ...prev, [qId]: opt }));
  
  const handleNavClick = (index) => {
    setVisited(prev => ({ ...prev, [index]: true }));
    if (viewMode === 'single') setCurrentQIndex(index);
    else questionRefs.current[index]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const getPaletteColor = (index, qId) => {
    if (viewMode === 'single' && currentQIndex === index) return "btn-primary";
    if (answers[qId]) return "btn-success"; 
    if (visited[index]) return "btn-danger"; 
    return "btn-outline-secondary";
  };

  if (loading) return <div className="vh-100 d-flex justify-content-center align-items-center page-bg"><div className="spinner-border text-primary"></div></div>;


  // ================= VIEW 1: DASHBOARD VIEW =================
  if (authStep === 'list') {
    return (
        <div>
            <Navbar title="Student Portal" />
            <div className="page-container">
                <PageHeader 
                    title={`Welcome, ${user?.username}`} 
                    subtitle="View your available and completed exams below." 
                />

                {/* ℹ️ EXAM DETAILS MODAL */}
            {showDetailsModal && examDetails && (
                <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.8)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                    <div className="bg-white p-5 rounded shadow-lg" style={{maxWidth: '500px', width: '90%'}}>
                        <h3 className="fw-bold mb-3 border-bottom pb-2"> Exam Details</h3>
                        <p className="fw-bold text-primary fs-5">{examDetails.title}</p>
                        
                        <ul className="list-group list-group-flush mb-4">
                            <li className="list-group-item d-flex justify-content-between px-0">
                                <span className="text-muted">Total Questions:</span>
                                <span className="fw-bold">{examDetails.question_count}</span>
                            </li>
                            <li className="list-group-item d-flex justify-content-between px-0">
                                <span className="text-muted">Total Marks:</span>
                                <span className="fw-bold">{examDetails.total_marks}</span>
                            </li>
                            <li className="list-group-item d-flex justify-content-between px-0">
                                <span className="text-muted">Duration:</span>
                                <span className="fw-bold">{examDetails.duration} minutes</span>
                            </li>
                            {examDetails.topics && examDetails.topics.length > 0 && (
                                <li className="list-group-item px-0">
                                    <span className="text-muted d-block mb-1">Topics Covered:</span>
                                    {examDetails.topics.map(t => <span key={t} className="badge bg-info me-1">{t}</span>)}
                                </li>
                            )}
                        </ul>

                        <div className="alert alert-warning small border-warning py-2 mb-4">
                            <strong className="d-block mb-1"> Proctoring Rules:</strong>
                            - Full screen is required.<br/>
                            - Maximum 3 tab switches allowed before auto-submit.<br/>
                            - Microphones must be enabled; loud noises will trigger warnings.
                        </div>
                        
                        <div className="d-flex gap-2">
                            <button className="btn btn-light w-50 fw-bold border" onClick={() => setShowDetailsModal(false)}>Cancel</button>
                            <button className="btn btn-primary w-50 fw-bold" onClick={handleProceedToAuth}>Proceed →</button>
                        </div>
                    </div>
                </div>
            )}

            {/*  EXAM PASSWORD MODAL */}
            {showPasswordPrompt && (
                <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.8)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                    <div className="bg-white p-5 rounded shadow-lg text-center" style={{maxWidth: '400px', width: '90%'}}>
                        <div className="text-primary mb-3" style={{fontSize: '3rem'}}></div>
                        <h3 className="fw-bold mb-3">Exam Password Required</h3>
                        <p className="text-muted mb-4">Please enter the password provided by your teacher to unlock this exam.</p>
                        
                        <input 
                            type="password" 
                            className="form-control form-control-lg mb-3 text-center fw-bold" 
                            placeholder="••••••••"
                            value={examPassword}
                            onChange={(e) => setExamPassword(e.target.value)}
                            onKeyDown={(e) => { if(e.key === 'Enter') handlePasswordSubmit(); }}
                        />
                        
                        {passwordError && <div className="text-danger small fw-bold mb-3 animate__animated animate__headShake">{passwordError}</div>}
                        
                        <div className="d-flex gap-2">
                            <button className="btn btn-light w-50 fw-bold border" onClick={() => setShowPasswordPrompt(false)}>Cancel</button>
                            <button className="btn btn-primary w-50 fw-bold" onClick={handlePasswordSubmit}>Unlock →</button>
                        </div>
                    </div>
                </div>
            )}

            {/*  REVIEW MODAL */}
            {reviewData && (
                <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                    <div className="bg-white p-4 rounded shadow-lg d-flex flex-column" style={{width: '90%', maxWidth: '800px', maxHeight: '90vh'}}>
                        <div className="d-flex justify-content-between align-items-center mb-4 border-bottom pb-2">
                            <h3 className="fw-bold m-0 text-dark"> Review: {reviewData.examTitle}</h3>
                            <button className="btn btn-light rounded-circle fw-bold" onClick={() => setReviewData(null)}>✕</button>
                        </div>
                        <div className="d-flex justify-content-between mb-3 bg-light p-3 rounded border">
                            <h5 className="text-primary fw-bold m-0">Score: {reviewData.score} / {reviewData.total}</h5>
                            <div className="text-end">
                                <span className={`badge ${reviewData.tab_switches > 0 ? 'bg-danger' : 'bg-success'} me-2`}>
                                    ️ {reviewData.tab_switches} Tab Violations
                                </span>
                                <span className={`badge ${reviewData.audio_warnings > 0 ? 'bg-warning text-dark' : 'bg-success'}`}>
                                     {reviewData.audio_warnings} Audio Warnings
                                </span>
                            </div>
                        </div>
                        <div className="overflow-auto flex-grow-1 pe-2">
                            {reviewData.questions.map((q, idx) => (
                                <div key={idx} className="card border-0 shadow-sm mb-3">
                                    <div className="card-body">
                                        <div className="d-flex justify-content-between align-items-start mb-2">
                                            <h6 className="fw-bold m-0">Q{idx+1}: {q.text}</h6>
                                            <span className={`badge ${q.is_subjective ? 'bg-info' : (q.is_correct ? 'bg-success' : 'bg-danger')}`}>
                                                {q.is_subjective ? 'Subjective' : (q.is_correct ? 'Correct' : 'Incorrect')}
                                            </span>
                                        </div>
                                        
                                        {q.is_subjective ? (
                                            <div className="bg-light p-3 rounded border">
                                                <div className="mb-2">
                                                    <span className="text-muted fw-bold d-block small mb-1">Your Answer:</span>
                                                    <p className="m-0 bg-white p-2 border rounded">{q.student_answer || <span className="text-muted italic">Not answered</span>}</p>
                                                </div>
                                                <div className="mb-2">
                                                    <span className="text-success fw-bold d-block small mb-1">Reference Answer:</span>
                                                    <p className="m-0 bg-white p-2 border rounded border-success">{q.reference_answer}</p>
                                                </div>
                                                <div className="d-flex justify-content-between align-items-center mt-3 pt-2 border-top">
                                                    <span className="fw-bold text-primary">Score: {q.marks_awarded !== null ? q.marks_awarded : 'Pending'} / 1.0</span>
                                                    {q.ai_explanation && <span className="badge bg-secondary cursor-pointer" title={q.ai_explanation}>AI Graded ℹ️</span>}
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="ms-2">
                                                {['A', 'B', 'C', 'D'].map(opt => {
                                                    const hashedOpt = hashText(String(opt).trim().toUpperCase());
                                                    let isCorrectAns = q.correct_option === hashedOpt;
                                                    let isStudentChoice = q.student_answer === hashedOpt;
                                                    
                                                    let optClass = "text-muted";
                                                    let icon = "";
                                                    
                                                    if (isCorrectAns) {
                                                        optClass = "text-success fw-bold bg-success bg-opacity-10 rounded p-1";
                                                        icon = "";
                                                    } else if (isStudentChoice && !isCorrectAns) {
                                                        optClass = "text-danger fw-bold bg-danger bg-opacity-10 rounded p-1";
                                                        icon = " (Your Choice)";
                                                    } else if (isStudentChoice) {
                                                        icon = "(Your Choice)";
                                                    }
                                                    
                                                    return (
                                                        <div key={opt} className={`mb-1 ${optClass}`}>
                                                            {opt}: {q.options[opt]} {icon}
                                                        </div>
                                                    );
                                                })}
                                                {!q.student_answer && <div className="text-warning fw-bold mt-2"> Not answered</div>}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            <div className="container py-5">
                <div className="d-flex justify-content-between align-items-center mb-5">
                    <div>
                        <h2 className="fw-bold m-0 text-dark">My Exams</h2>
                        <p className="text-muted m-0">Select an exam to begin your assessment.</p>
                    </div>
                    {user && <span className="badge bg-white text-dark shadow-sm px-3 py-2 border">User ID: {user.id}</span>}
                </div>

                <div className="row g-4 align-items-start">
                    {exams.map(exam => {
                        const { start, end } = getExamTimes(exam);
                        const status = getExamStatus(exam);
                        return (
                            <div key={exam.id} className="col-md-6 col-lg-4">
                                <div className="card h-100 p-3 glass-card">
                                    <div className="d-flex justify-content-between align-items-start mb-3">
                                        <div className="bg-light rounded-circle d-flex align-items-center justify-content-center text-primary" 
                                             style={{width:'50px', height:'50px', background: '#e3f2fd'}}>
                                            <FileText size={24} />
                                        </div>
                                        <span className={`badge rounded-pill px-3 py-2 bg-${status.color === 'warning' ? 'warning text-dark' : status.color}`}>
                                            {status.label}
                                        </span>
                                    </div>
                                    
                                    <h5 className="fw-bold text-dark mb-1 d-flex align-items-center gap-2">
                                        {exam.title} {exam.has_password && <Lock size={16} title="Password Protected" />}
                                    </h5>
                                    <p className="text-muted small mb-4 d-flex align-items-center gap-1"><Clock size={14} /> {exam.duration} mins duration</p>
                                    
                                    <div className="mt-auto bg-light rounded p-3 mb-3 small border">
                                        {exam.slotting_enabled && (
                                            <div className="mb-2 text-center text-primary fw-bold" style={{fontSize: '0.8rem'}}>
                                                <AlertTriangle size={14} className="me-1" />
                                                {exam.assigned_slot ? 'Assigned Slot' : 'Not Assigned To Slot'}
                                            </div>
                                        )}
                                        <div className="d-flex justify-content-between mb-1">
                                            <span className="text-muted">{exam.assigned_slot ? 'Slot Opens:' : 'Opens:'}</span>
                                            <span className="fw-bold text-dark">{formatDateDisplay(start)}</span>
                                        </div>
                                        <div className="d-flex justify-content-between">
                                            <span className="text-muted">{exam.assigned_slot ? 'Slot Closes:' : 'Closes:'}</span>
                                            <span className="fw-bold text-dark">{formatDateDisplay(end)}</span>
                                        </div>
                                    </div>

                                    <button 
                                        onClick={() => {
                                            if (status.action === 'review') handleReviewExam(exam);
                                            else if (!status.disabled) handleSelectExam(exam);
                                        }} 
                                        disabled={status.disabled && status.action !== 'review'}
                                        className={`btn w-100 fw-bold py-2 btn-${status.color}`}
                                        style={{borderRadius: '10px'}}
                                    >
                                        {status.action === 'review' ? " Review Results" : `${status.icon} ${status.label}`}
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
      </div>
    );
  }

  // ================= VIEW 2: LOBBY =================
  if (authStep === 'auth') {
      return (
          <PreExamAuth 
              exam={activeExam} 
              onSuccess={handleAuthSuccess} 
              onCancel={() => setAuthStep('list')} 
          />
      );
  }

  // ================= VIEW 3: EXAM INTERFACE VIEW =================
  const currentQ = questions[currentQIndex];

  //  ENFORCE INITIAL FULL SCREEN BEFORE SHOWING EXAM
  if (authStep === 'exam' && !isFullscreen && !hasEnteredFullScreenRef.current) {
      return (
          <div className="vh-100 d-flex flex-column justify-content-center align-items-center page-bg p-4" style={{ backgroundColor: '#f0f2f5' }}>
              <div className="text-center p-5 bg-white text-dark rounded shadow-lg" style={{maxWidth: '600px', borderTop: '5px solid #ff6b6b'}}>
                  <h1 style={{fontSize: '4rem', marginBottom: '20px'}}>️</h1>
                  <h3 className="fw-bold mb-3">Full Screen Required</h3>
                  <p className="text-muted mb-4" style={{ lineHeight: '1.6' }}>
                      To maintain exam integrity, this assessment must be taken in full-screen mode. <br/><br/>
                      <strong>Warning:</strong> Pressing <code>ESC</code> or exiting full screen during the test will result in a penalty warning.
                  </p>
                  <button className="btn btn-primary btn-lg w-100 fw-bold py-3 shadow-sm" onClick={enterFullScreen} style={{ borderRadius: '10px' }}>
                      Enter Full Screen & Begin Exam
                  </button>
              </div>
          </div>
      );
  }

  return (
    <>
      {showCheatWarning && (
          <div className="warning-overlay">
              <h1 style={{fontSize: '5rem', marginBottom: '20px'}}></h1>
              <h1 className="fw-bold mb-4 text-center">VIOLATION DETECTED</h1>
              <h4 className="mb-5 text-center px-4" style={{maxWidth: '700px', lineHeight: '1.6'}}>
                  You switched tabs, exited full screen, or clicked outside the exam window. <br/><br/>
                  This is <strong>Warning {warnings} of {MAX_WARNINGS}</strong>. 
                  <br/><br/>
                  On your 3rd warning, your exam will automatically submit.
              </h4>
              <button className="btn btn-light btn-lg fw-bold px-5 py-3 shadow" style={{borderRadius: '50px'}} 
                  onClick={() => {
                      enterFullScreen(); //  FORCE BACK TO FULL SCREEN TO CLEAR WARNING
                      setShowCheatWarning(false);
                  }}>
                  I Understand, Return to Exam
              </button>
          </div>
      )}

      <div 
        className="d-flex flex-column vh-100 exam-bg" 
        style={{ userSelect: 'none', WebkitUserSelect: 'none', MozUserSelect: 'none', msUserSelect: 'none' }}
      >
        <div className="bg-white shadow-sm d-flex justify-content-between align-items-center px-4 py-2" style={{height: '65px', zIndex: 10}}>
          <div className="d-flex align-items-center gap-3">
               <div className="bg-light px-3 py-1 rounded fw-bold text-primary border border-primary">⏱️ {formatTime(timeLeft)}</div>
               {warnings > 0 && (<div className="bg-danger px-3 py-1 rounded fw-bold text-white"> Warnings: {warnings}/{MAX_WARNINGS}</div>)}
               <div className="vr"></div>
               <span className="fw-bold text-dark fs-5">{activeExam.title}</span>
          </div>
          <button className="btn btn-dark px-4 fw-bold rounded-pill" onClick={() => submitExam(false)}>Finish & Submit</button>
        </div>

        {showAlert && (
          <div className="bg-danger text-white text-center fw-bold py-2 small animate__animated animate__headShake">
               AI WARNING: { proctorStatus === "missing" ? "Face Not Detected!" : proctorStatus === "multiple" ? "Multiple Faces Detected!" : proctorStatus === "looking_away" ? "You are looking away from the screen!" : proctorStatus === "phone_detected" ? "Cell Phone Detected in Frame!" : proctorStatus === "book_detected" ? "Book or Notes Detected!" : "Suspicious Activity!" }
          </div>
        )}
        {showAudioAlert && (
          <div className="bg-danger text-white text-center fw-bold py-2 small animate__animated animate__headShake"> AUDIO WARNING: Loud noise or talking detected in your environment!</div>
        )}

        <div className="d-flex flex-grow-1 overflow-hidden">
          <div className="flex-grow-1 p-5 overflow-auto d-flex justify-content-center">
              {currentQ ? (
                  <div className="d-flex flex-column w-100 question-container">
                      <div className="d-flex justify-content-end mb-3">
                           <div className="btn-group shadow-sm">
                              <button className={`btn btn-sm ${viewMode==='single' ? 'btn-primary' : 'btn-white bg-white'}`} onClick={()=>setViewMode('single')}>Single</button>
                              <button className={`btn btn-sm ${viewMode==='list' ? 'btn-primary' : 'btn-white bg-white'}`} onClick={()=>setViewMode('list')}>List</button>
                           </div>
                      </div>

                      {viewMode === 'single' && (
                          <div className="card shadow-sm border-0 p-5 mb-3 bg-white question-card">
                              <div className="d-flex justify-content-between mb-4 border-bottom pb-3">
                                  <h5 className="text-secondary m-0">Question {currentQIndex+1} <span className="text-muted small">/ {questions.length}</span></h5>
                                  <span className="badge bg-light text-dark border">
                                      {currentQ.is_subjective ? 'Subjective' : 'Single Choice'}
                                  </span>
                              </div>
                              <p className="lead fw-bold text-dark mb-5" style={{lineHeight: '1.6'}}>{currentQ.text}</p>
                              
                              {currentQ.is_subjective ? (
                                  <textarea 
                                      className="form-control" 
                                      rows="6" 
                                      placeholder="Type your answer here..."
                                      value={answers[currentQ.id] || ''}
                                      onChange={(e) => handleOptionSelect(currentQ.id, e.target.value)}
                                  ></textarea>
                              ) : (
                                  <div className="d-flex flex-column gap-3">
                                      {['A','B','C','D'].map(opt => (
                                          <div key={opt} onClick={()=>handleOptionSelect(currentQ.id, opt)} className={`option-card ${answers[currentQ.id]===opt ? 'selected' : ''}`}>
                                              <div className="d-flex align-items-center">
                                                  <div className={`rounded-circle d-flex align-items-center justify-content-center me-3 option-circle ${answers[currentQ.id]===opt ? 'selected' : 'unselected'}`}>{opt}</div>
                                                  <span className="fs-6">{currentQ.options[opt]}</span>
                                              </div>
                                          </div>
                                      ))}
                                  </div>
                              )}
                          </div>
                      )}

                      {viewMode === 'list' && (
                          <div className="d-flex flex-column gap-4">
                              {questions.map((q, idx) => (
                                  <div key={q.id} ref={el => questionRefs.current[idx] = el} className="card border-0 shadow-sm p-4">
                                      <h6 className="fw-bold text-muted">Q{idx+1}</h6>
                                      <p className="fw-bold">{q.text}</p>
                                      
                                      {q.is_subjective ? (
                                          <textarea 
                                              className="form-control" 
                                              rows="4" 
                                              placeholder="Type your answer here..."
                                              value={answers[q.id] || ''}
                                              onChange={(e) => handleOptionSelect(q.id, e.target.value)}
                                          ></textarea>
                                      ) : (
                                          <div className="d-flex flex-column gap-2">
                                              {['A','B','C','D'].map(opt => (
                                                  <div key={opt} onClick={()=>handleOptionSelect(q.id, opt)} className={`option-card p-2 ${answers[q.id]===opt ? 'selected' : ''}`}>
                                                      <small className="fw-bold me-2">{opt}:</small> {q.options[opt]}
                                                  </div>
                                              ))}
                                          </div>
                                      )}
                                  </div>
                              ))}
                          </div>
                      )}

                      {viewMode === 'single' && (
                          <div className="d-flex justify-content-between mt-3">
                             <button className="btn btn-white bg-white shadow-sm px-4 border" disabled={currentQIndex===0} onClick={()=>handleNavClick(currentQIndex-1)}>← Previous</button>
                             <button className="btn btn-primary shadow-sm px-5" disabled={currentQIndex===questions.length-1} onClick={()=>handleNavClick(currentQIndex+1)}>Next Question →</button>
                          </div>
                      )}
                  </div>
              ) : (
                  <div className="text-center w-100 mt-5"><div className="spinner-border text-primary"></div></div>
              )}
          </div>

          <div className="bg-white border-start d-flex flex-column p-0 shadow-sm sidebar">
               <div className="p-3 border-bottom bg-light">
                  <h6 className="m-0 fw-bold text-dark">Question Palette</h6>
               </div>
               <div className="flex-grow-1 p-3 overflow-auto">
                   <div className="d-flex flex-wrap gap-2 justify-content-start">
                      {questions.map((q, i) => (
                          <button key={q.id} className={`btn btn-sm fw-bold ${getPaletteColor(i, q.id)}`} style={{width:'40px', height:'40px', borderRadius:'8px'}} onClick={()=>handleNavClick(i)}>{i+1}</button>
                      ))}
                   </div>
                   <div className="mt-4 p-3 rounded bg-light border small text-muted">
                      <div className="row g-2">
                          <div className="col-6 d-flex align-items-center gap-2"><div className="bg-success rounded-circle" style={{width:8, height:8}}></div> Answered</div>
                          <div className="col-6 d-flex align-items-center gap-2"><div className="bg-primary rounded-circle" style={{width:8, height:8}}></div> Current</div>
                          <div className="col-6 d-flex align-items-center gap-2"><div className="bg-danger rounded-circle" style={{width:8, height:8}}></div> Visited</div>
                          <div className="col-6 d-flex align-items-center gap-2"><div className="border border-secondary rounded-circle" style={{width:8, height:8}}></div> Unvisited</div>
                      </div>
                   </div>
               </div>
               <div className="p-3 border-top bg-light text-center">
                  <small className="d-block mb-2 text-muted fw-bold">Live Proctoring Active  </small>
                  <div className="rounded overflow-hidden border mx-auto shadow-sm proctor-container bg-dark" style={{ height: '120px' }}>
                      <Webcam audio={false} ref={proctorWebcamRef} screenshotFormat="image/jpeg" mirrored={true} style={{ width: '100%', height: '100%', objectFit: 'cover' }} videoConstraints={{ facingMode: "user" }} />
                  </div>
               </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default StudentDashboard;