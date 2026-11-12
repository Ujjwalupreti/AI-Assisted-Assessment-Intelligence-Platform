import React from 'react';
import MetricCard from '../common/MetricCard';

const QualityAnalysis = ({ averageQuality }) => {
    // If quality score is between 0 and 1, convert to percentage
    const safeQuality = (averageQuality && averageQuality <= 1) ? averageQuality * 100 : averageQuality;
    const qualityScore = safeQuality ? Math.round(safeQuality) : 0;
    
    let colorClass = 'text-success';
    if (qualityScore < 70) colorClass = 'text-danger';
    else if (qualityScore < 85) colorClass = 'text-warning';

    return (
        <MetricCard 
            title="Question Quality" 
            value={<span className={colorClass}>{qualityScore}%</span>} 
            subtitle="Average AI quality score"
        />
    );
};

export default QualityAnalysis;
