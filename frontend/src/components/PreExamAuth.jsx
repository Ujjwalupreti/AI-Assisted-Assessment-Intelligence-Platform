import React, { useState, useRef } from 'react';
import Webcam from "react-webcam";

const PreExamAuth = ({ exam, onSuccess, onCancel }) => {
    const webcamRef = useRef(null);
    const [step, setStep] = useState('id_capture'); 
    const [idImage, setIdImage] = useState(null);

    const captureId = () => {
        const imageSrc = webcamRef.current.getScreenshot();
        setIdImage(imageSrc);
        setStep('face_capture');
    };

    const captureFace = () => {
        const faceImage = webcamRef.current.getScreenshot();
        // Send both images back to the main dashboard when done
        onSuccess(idImage, faceImage);
    };

    return (
        <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-main)', color: 'var(--text-primary)' }}>
            <div style={{ width: '100%', padding: '1.5rem', display: 'flex', justifyContent: 'space-between', position: 'absolute', top: 0, left: 0 }}>
                <h4 style={{ fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>{exam.title} - Security Check</h4>
                <button className="btn btn-ghost" onClick={onCancel}>Cancel & Exit</button>
            </div>

            <h2 style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Pre-Exam Authentication</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', fontSize: '1.25rem' }}>
                {step === 'id_capture' ? "Step 1: Please hold your Student ID to the camera." : "Step 2: Please look directly at the camera."}
            </p>
            
            <div style={{ padding: '0.5rem', borderRadius: '8px', boxShadow: 'var(--shadow-md)', marginBottom: '2rem', border: '2px solid var(--border)', background: 'var(--surface-secondary)' }}>
                <Webcam audio={false} ref={webcamRef} screenshotFormat="image/jpeg" width={500} height={375} videoConstraints={{ facingMode: "user" }} />
            </div>

            {step === 'id_capture' ? (
                <button className="btn btn-primary" style={{ padding: '1rem 3rem', borderRadius: '50px', fontWeight: 600, fontSize: '1.1rem' }} onClick={captureId}> Capture ID Card</button>
            ) : (
                <button className="btn btn-success" style={{ padding: '1rem 3rem', borderRadius: '50px', fontWeight: 600, fontSize: '1.1rem' }} onClick={captureFace}> Capture Face & Start Exam</button>
            )}
        </div>
    );
};

export default PreExamAuth;
