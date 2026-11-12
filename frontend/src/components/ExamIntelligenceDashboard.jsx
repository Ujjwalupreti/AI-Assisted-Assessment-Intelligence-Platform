import React, { useState, useEffect } from 'react';
import { intelligenceService } from '../services/intelligenceService';
import { examService } from '../services/examService';

import LoadingState from './common/LoadingState';
import EmptyState from './common/EmptyState';
import SectionHeader from './common/SectionHeader';

import BloomDistribution from './intelligence/BloomDistribution';
import DifficultyDistribution from './intelligence/DifficultyDistribution';
import TopicCoverage from './intelligence/TopicCoverage';
import QualityAnalysis from './intelligence/QualityAnalysis';
import DuplicateAnalysis from './intelligence/DuplicateAnalysis';
import AIRecommendations from './intelligence/AIRecommendations';
import JobProgress from './intelligence/JobProgress';
import RecommendationPanel from './intelligence/RecommendationPanel';
import SlotGenerator from './intelligence/SlotGenerator';

const ExamIntelligenceDashboard = ({ examId }) => {
    const [report, setReport] = useState(null);
    const [blueprint, setBlueprint] = useState(null);
    const [loading, setLoading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    
    // AI Recommendations state
    const [generating, setGenerating] = useState(false);
    const [gapTopic, setGapTopic] = useState('');
    const [gapBloom, setGapBloom] = useState('Remember');
    const [gapDifficulty, setGapDifficulty] = useState('Medium');
    const [useRag, setUseRag] = useState(false);
    const [generatedQuestion, setGeneratedQuestion] = useState(null);

    const fetchData = async () => {
        setLoading(true);
        try {
            // Fetch both report and exam details (for blueprint) in parallel
            const [reportData, examData] = await Promise.all([
                intelligenceService.getReport(examId).catch(() => null),
                examService.getExamDetails(examId).catch(() => null)
            ]);
            
            if (reportData) setReport(reportData);
            
            if (examData && examData.blueprint_json) {
                try {
                    setBlueprint(JSON.parse(examData.blueprint_json));
                } catch (e) {
                    console.error("Failed to parse blueprint", e);
                }
            }
        } catch (error) {
            console.error("Error fetching intelligence data", error);
        }
        setLoading(false);
    };

    useEffect(() => {
        if (examId) fetchData();
    }, [examId]);

    const [activeJobId, setActiveJobId] = useState(null);

    const handleAnalyzeAll = async () => {
        setAnalyzing(true);
        try {
            const res = await intelligenceService.analyzeAll(examId);
            if (res.job_id) {
                setActiveJobId(res.job_id);
            } else {
                alert("Analysis complete!");
                await fetchData();
            }
        } catch (error) {
            console.error("Error analyzing all", error);
            alert(`Error: ${error.message}`);
        }
        setAnalyzing(false);
    };

    const handleJobComplete = async () => {
        setActiveJobId(null);
        await fetchData();
    };

    const handleJobFail = (failedIds) => {
        setActiveJobId(null);
        alert(`Analysis failed for some questions: ${failedIds.join(', ')}`);
        fetchData();
    };

    const handleGenerateGapQuestion = async () => {
        setGenerating(true);
        try {
            const data = await intelligenceService.generateGapQuestions(examId, {
                topic: gapTopic,
                bloom_level: gapBloom,
                difficulty: gapDifficulty,
                use_rag: useRag
            });
            setGeneratedQuestion(data);
        } catch (error) {
            console.error("Error generating question", error);
            alert("Failed to generate question");
        }
        setGenerating(false);
    };

    // Calculate Assessment Readiness (0-100)
    // Basic heuristic: average of quality and (if analysis exists) presence of questions
    const readinessScore = report 
        ? Math.round((report.average_quality * 100 + (report.total_questions > 0 ? 100 : 0)) / 2) 
        : 0;

    return (
        <div className="card shadow-sm mb-4 border-0" style={{ borderRadius: '15px', background: 'var(--surface)' }}>
            <div className="card-header d-flex justify-content-between align-items-center py-3" style={{ borderTopLeftRadius: '15px', borderTopRightRadius: '15px' }}>
                <h5 className="mb-0 fw-bold" style={{ color: 'var(--text-primary)' }}> Exam Intelligence Dashboard</h5>
                <button 
                    className="btn btn-sm btn-primary fw-bold px-4" 
                    onClick={handleAnalyzeAll} 
                    disabled={analyzing}
                >
                    {analyzing ? (
                        <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Analyzing...</>
                    ) : (
                        "Analyze Entire Exam"
                    )}
                </button>
            </div>
            
            <div className="card-body p-4" style={{ background: 'var(--surface)' }}>
                {activeJobId && (
                    <JobProgress 
                        jobId={activeJobId} 
                        onComplete={handleJobComplete} 
                        onFail={handleJobFail} 
                    />
                )}

                {loading && <LoadingState message="Loading intelligence report..." />}
                
                {!loading && !report && !activeJobId && (
                    <EmptyState 
                        message="No analysis data yet. Click 'Analyze Entire Exam' to build the intelligence report."
                    />
                )}
                
                {!loading && report && (
                    <>
                        <SectionHeader 
                            title="Overall Assessment Health" 
                            subtitle="High-level metrics and quality indicators."
                            action={
                                <div className="text-end">
                                    <div className="small text-muted fw-bold text-uppercase">Assessment Readiness</div>
                                    <h3 className={`mb-0 ${readinessScore >= 80 ? 'text-success' : readinessScore >= 60 ? 'text-warning' : 'text-danger'}`}>
                                        {readinessScore} <span className="small text-muted">/ 100</span>
                                    </h3>
                                </div>
                            }
                        />

                        <div className="row g-4 mb-5 align-items-start">
                            <div className="col-md-4">
                                <QualityAnalysis averageQuality={report.average_quality} />
                            </div>
                            <div className="col-md-4">
                                <DuplicateAnalysis examId={examId} duplicateSafety={report.duplicate_safety !== undefined ? report.duplicate_safety : 100} />
                            </div>
                            <div className="col-md-4">
                                <div className="card shadow-sm h-100 border-0" style={{ background: 'var(--surface-secondary)' }}>
                                    <div className="card-body p-4 text-center">
                                        <h6 className="card-title fw-bold text-uppercase mb-2" style={{ color: 'var(--text-secondary)' }}>Total Questions</h6>
                                        <h1 className="mb-1 display-4 fw-bold text-primary">{report.total_questions}</h1>
                                        <small className="text-muted">Analyzed by AI</small>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <SectionHeader 
                            title="Blueprint vs Actual" 
                            subtitle="Compare current exam composition against your target blueprint."
                        />

                        <div className="row g-4 mb-5">
                            <div className="col-md-4">
                                <BloomDistribution 
                                    data={report.bloom_distribution} 
                                    targetData={blueprint?.bloom_distribution}
                                    totalQuestions={report.total_questions}
                                />
                            </div>
                            <div className="col-md-4">
                                <DifficultyDistribution 
                                    data={report.difficulty_distribution} 
                                    targetData={blueprint?.difficulty_distribution}
                                    totalQuestions={report.total_questions}
                                />
                            </div>
                            <div className="col-md-4">
                                <TopicCoverage 
                                    data={report.topic_distribution} 
                                    targetData={blueprint?.topic_distribution}
                                    totalQuestions={report.total_questions}
                                />
                            </div>
                        </div>

                        <RecommendationPanel 
                            examId={examId} 
                            onQuestionAdded={() => fetchData()} 
                        />

                        <SlotGenerator examId={examId} />

                        <SectionHeader 
                            title="Manual Generation" 
                            subtitle="Manually generate gap-filling questions with AI." 
                        />
                        <AIRecommendations 
                            examId={examId}
                            gapTopic={gapTopic}
                            setGapTopic={setGapTopic}
                            gapBloom={gapBloom}
                            setGapBloom={setGapBloom}
                            gapDifficulty={gapDifficulty}
                            setGapDifficulty={setGapDifficulty}
                            useRag={useRag}
                            setUseRag={setUseRag}
                            onGenerateGap={handleGenerateGapQuestion}
                            generating={generating}
                            generatedQuestion={generatedQuestion}
                        />
                    </>
                )}
            </div>
        </div>
    );
};

export default ExamIntelligenceDashboard;
