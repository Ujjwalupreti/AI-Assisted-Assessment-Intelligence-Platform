import React, { useMemo } from 'react';

/**
 * AutomataDiagramViewer
 * Renders a crisp, interactive SVG state-transition diagram for DFA / NFA automata.
 * Features:
 * - Start state indicator with incoming 'Start' arrow
 * - Concentric double circles for accepting/final states
 * - Directed bezier curves with arrowheads for transitions
 * - Self-loop arcs above nodes with transition symbols
 * - Bidirectional curve separation to avoid overlapping edges
 * - Tooltips and legend for complete formal clarity
 */
const AutomataDiagramViewer = ({ automataData, height = 260, title, readOnly = true }) => {
    // Parse data safely if passed as string or nested object
    const parsedData = useMemo(() => {
        if (!automataData) return null;
        let d = automataData;
        if (typeof d === 'string') {
            try {
                d = JSON.parse(d);
            } catch {
                return null;
            }
        }
        if (d && d.automata) d = d.automata;
        
        const type = (d.type || 'DFA').toUpperCase();
        let states = Array.isArray(d.states) ? d.states.map(String).map(s => s.trim()).filter(Boolean) : [];
        const alphabet = Array.isArray(d.alphabet) ? d.alphabet.map(String).map(s => s.trim()).filter(Boolean) : ['0', '1'];
        const initialState = String(d.initial_state || d.start_state || (states[0] || 'q0')).trim();
        const finalStates = Array.isArray(d.final_states || d.accept_states) 
            ? (d.final_states || d.accept_states).map(String).map(s => s.trim()).filter(Boolean) 
            : [];

        // Parse transitions
        let transitions = [];
        if (Array.isArray(d.transitions)) {
            transitions = d.transitions.map(t => ({
                from: String(t.from || '').trim(),
                symbol: String(t.symbol !== undefined ? t.symbol : (t.input || '')).trim(),
                to: String(t.to || '').trim()
            })).filter(t => t.from && t.to);
        } else if (typeof d.transitions === 'object' && d.transitions !== null) {
            // dict of dicts: {"q0": {"0": "q1", "1": "q0"}}
            for (const [fromSt, trans] of Object.entries(d.transitions)) {
                if (typeof trans === 'object' && trans !== null) {
                    for (const [sym, toSt] of Object.entries(trans)) {
                        if (Array.isArray(toSt)) {
                            toSt.forEach(target => transitions.push({ from: fromSt, symbol: sym, to: String(target) }));
                        } else {
                            transitions.push({ from: fromSt, symbol: sym, to: String(toSt) });
                        }
                    }
                }
            }
        }

        // Infer any missing states mentioned in transitions
        transitions.forEach(t => {
            if (!states.includes(t.from)) states.push(t.from);
            if (!states.includes(t.to)) states.push(t.to);
        });

        if (states.length === 0) states = ['q0'];
        if (!states.includes(initialState)) states.unshift(initialState);

        return { type, states, alphabet, initialState, finalStates, transitions };
    }, [automataData]);

    if (!parsedData) {
        return (
            <div className="alert alert-light border text-muted small p-3 text-center my-2">
                <em>No valid DFA/NFA state diagram data to render.</em>
            </div>
        );
    }

    const { type, states, alphabet, initialState, finalStates, transitions } = parsedData;

    // Viewbox dimensions
    const svgWidth = 560;
    const svgHeight = height || 260;
    const nodeRadius = 24;

    // Calculate node coordinates
    const nodeCoords = useMemo(() => {
        const coords = {};
        const N = states.length;
        if (N === 1) {
            coords[states[0]] = { x: svgWidth / 2, y: svgHeight / 2 };
        } else if (N <= 4) {
            // Linear horizontal layout with vertical breathing room
            const startX = 110;
            const endX = svgWidth - 70;
            const stepX = (endX - startX) / (N - 1);
            const centerY = svgHeight / 2 + 10;
            states.forEach((st, idx) => {
                coords[st] = { x: startX + idx * stepX, y: centerY };
            });
        } else {
            // Circular/elliptical layout for 5+ states
            const cx = svgWidth / 2;
            const cy = svgHeight / 2 + 10;
            const rx = (svgWidth / 2) - 80;
            const ry = (svgHeight / 2) - 50;
            states.forEach((st, idx) => {
                const angle = (2 * Math.PI * idx) / N - Math.PI / 2;
                coords[st] = {
                    x: cx + rx * Math.cos(angle),
                    y: cy + ry * Math.sin(angle)
                };
            });
        }
        return coords;
    }, [states, svgWidth, svgHeight]);

    // Group transitions by pair (from -> to) to merge symbols like "0, 1"
    const groupedTransitions = useMemo(() => {
        const map = new Map();
        transitions.forEach(t => {
            const key = `${t.from}:::${t.to}`;
            if (!map.has(key)) {
                map.set(key, { from: t.from, to: t.to, symbols: [] });
            }
            const group = map.get(key);
            if (!group.symbols.includes(t.symbol)) {
                group.symbols.push(t.symbol || 'ε');
            }
        });
        return Array.from(map.values());
    }, [transitions]);

    // Determine if reverse transition exists for bending arcs
    const hasReverse = (from, to) => {
        if (from === to) return false;
        return groupedTransitions.some(g => g.from === to && g.to === from);
    };

    return (
        <div className="automata-diagram-viewer bg-white rounded border p-2 my-2 shadow-sm">
            {/* Header with formal definition */}
            <div className="d-flex justify-content-between align-items-center mb-1 px-2 border-bottom pb-1">
                <div className="d-flex align-items-center gap-2">
                    <span className="badge bg-primary text-uppercase fw-bold" style={{ fontSize: '11px' }}>
                        {type} Diagram
                    </span>
                    <span className="text-secondary small">
                        <strong>Q:</strong> {'{' + states.join(', ') + '}'} | <strong>Σ:</strong> {'{' + alphabet.join(', ') + '}'}
                    </span>
                </div>
                <div className="d-flex align-items-center gap-2 small text-muted">
                    <span><strong className="text-primary">q₀:</strong> {initialState}</span>
                    <span><strong className="text-success">F:</strong> {'{' + (finalStates.join(', ') || '∅') + '}'}</span>
                </div>
            </div>

            {/* SVG Canvas */}
            <div className="svg-container position-relative d-flex justify-content-center overflow-auto" style={{ maxHeight: `${svgHeight + 20}px` }}>
                <svg
                    viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                    width="100%"
                    height={svgHeight}
                    style={{ minWidth: '420px', maxWidth: '640px', background: '#fafbfc', borderRadius: '6px' }}
                >
                    <defs>
                        {/* Standard directed arrow marker */}
                        <marker
                            id="automata-arrow"
                            viewBox="0 0 10 10"
                            refX="9"
                            refY="5"
                            markerWidth="6"
                            markerHeight="6"
                            orient="auto-start-reverse"
                        >
                            <path d="M 0 1 L 10 5 L 0 9 z" fill="#2563eb" />
                        </marker>

                        {/* Start state incoming arrow marker */}
                        <marker
                            id="automata-start-arrow"
                            viewBox="0 0 10 10"
                            refX="9"
                            refY="5"
                            markerWidth="7"
                            markerHeight="7"
                            orient="auto"
                        >
                            <path d="M 0 1 L 10 5 L 0 9 z" fill="#059669" />
                        </marker>

                        {/* Drop shadow filter for states */}
                        <filter id="node-shadow" x="-20%" y="-20%" width="140%" height="140%">
                            <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.12" />
                        </filter>
                    </defs>

                    {/* 1. START STATE POINTER */}
                    {nodeCoords[initialState] && (
                        <g className="start-pointer">
                            <line
                                x1={nodeCoords[initialState].x - 48}
                                y1={nodeCoords[initialState].y}
                                x2={nodeCoords[initialState].x - nodeRadius - 3}
                                y2={nodeCoords[initialState].y}
                                stroke="#059669"
                                strokeWidth="2.5"
                                markerEnd="url(#automata-start-arrow)"
                            />
                            <text
                                x={nodeCoords[initialState].x - 52}
                                y={nodeCoords[initialState].y - 6}
                                fill="#059669"
                                fontSize="10"
                                fontWeight="bold"
                                textAnchor="end"
                            >
                                Start
                            </text>
                        </g>
                    )}

                    {/* 2. TRANSITIONS (EDGES & LOOPS) */}
                    {groupedTransitions.map((gt, idx) => {
                        const fromCoord = nodeCoords[gt.from];
                        const toCoord = nodeCoords[gt.to];
                        if (!fromCoord || !toCoord) return null;

                        const labelText = gt.symbols.join(', ');

                        // Self Loop (u == v)
                        if (gt.from === gt.to) {
                            const loopX = fromCoord.x;
                            const loopY = fromCoord.y - nodeRadius;
                            const d = `M ${loopX - 12} ${loopY + 2} C ${loopX - 30} ${loopY - 45}, ${loopX + 30} ${loopY - 45}, ${loopX + 12} ${loopY + 2}`;

                            return (
                                <g key={`self-${idx}`} className="transition-edge">
                                    <path
                                        d={d}
                                        fill="none"
                                        stroke="#2563eb"
                                        strokeWidth="2"
                                        markerEnd="url(#automata-arrow)"
                                    />
                                    {/* Label Pill */}
                                    <rect
                                        x={loopX - Math.max(12, labelText.length * 4.5)}
                                        y={loopY - 56}
                                        width={Math.max(24, labelText.length * 9)}
                                        height="16"
                                        rx="4"
                                        fill="#ffffff"
                                        stroke="#93c5fd"
                                        strokeWidth="1"
                                    />
                                    <text
                                        x={loopX}
                                        y={loopY - 44}
                                        fill="#1e40af"
                                        fontSize="11"
                                        fontWeight="bold"
                                        textAnchor="middle"
                                    >
                                        {labelText}
                                    </text>
                                </g>
                            );
                        }

                        // Different Nodes (u != v)
                        const dx = toCoord.x - fromCoord.x;
                        const dy = toCoord.y - fromCoord.y;
                        const dist = Math.sqrt(dx * dx + dy * dy);
                        if (dist === 0) return null;

                        const unitX = dx / dist;
                        const unitY = dy / dist;

                        const reverseExists = hasReverse(gt.from, gt.to);

                        // If reverse exists or curved styling, bend curve
                        let pathD = '';
                        let midLabelX = 0;
                        let midLabelY = 0;

                        if (reverseExists) {
                            // Curve perpendicular to line
                            const perpX = -unitY;
                            const perpY = unitX;
                            const curveOffset = 26;

                            const ctrlX = (fromCoord.x + toCoord.x) / 2 + perpX * curveOffset;
                            const ctrlY = (fromCoord.y + toCoord.y) / 2 + perpY * curveOffset;

                            // Adjust start and end to touch node perimeter
                            const startX = fromCoord.x + unitX * nodeRadius + perpX * 8;
                            const startY = fromCoord.y + unitY * nodeRadius + perpY * 8;
                            const endX = toCoord.x - unitX * (nodeRadius + 4) + perpX * 8;
                            const endY = toCoord.y - unitY * (nodeRadius + 4) + perpY * 8;

                            pathD = `M ${startX} ${startY} Q ${ctrlX} ${ctrlY} ${endX} ${endY}`;
                            midLabelX = (ctrlX + (fromCoord.x + toCoord.x) / 2) / 2;
                            midLabelY = (ctrlY + (fromCoord.y + toCoord.y) / 2) / 2;
                        } else {
                            // Straight or very gentle arc
                            const startX = fromCoord.x + unitX * nodeRadius;
                            const startY = fromCoord.y + unitY * nodeRadius;
                            const endX = toCoord.x - unitX * (nodeRadius + 4);
                            const endY = toCoord.y - unitY * (nodeRadius + 4);

                            pathD = `M ${startX} ${startY} L ${endX} ${endY}`;
                            midLabelX = (startX + endX) / 2 - unitY * 12;
                            midLabelY = (startY + endY) / 2 + unitX * 12;
                        }

                        return (
                            <g key={`edge-${idx}`} className="transition-edge">
                                <path
                                    d={pathD}
                                    fill="none"
                                    stroke="#2563eb"
                                    strokeWidth="2"
                                    markerEnd="url(#automata-arrow)"
                                />
                                {/* Label Pill */}
                                <rect
                                    x={midLabelX - Math.max(10, labelText.length * 4)}
                                    y={midLabelY - 8}
                                    width={Math.max(20, labelText.length * 8)}
                                    height="16"
                                    rx="4"
                                    fill="#ffffff"
                                    stroke="#93c5fd"
                                    strokeWidth="1"
                                />
                                <text
                                    x={midLabelX}
                                    y={midLabelY + 4}
                                    fill="#1e40af"
                                    fontSize="11"
                                    fontWeight="bold"
                                    textAnchor="middle"
                                >
                                    {labelText}
                                </text>
                            </g>
                        );
                    })}

                    {/* 3. STATES (CIRCLES & LABELS) */}
                    {states.map(st => {
                        const coord = nodeCoords[st];
                        if (!coord) return null;

                        const isInitial = st === initialState;
                        const isFinal = finalStates.includes(st);

                        return (
                            <g key={`node-${st}`} className="automata-state" filter="url(#node-shadow)">
                                {/* Outer circle */}
                                <circle
                                    cx={coord.x}
                                    cy={coord.y}
                                    r={nodeRadius}
                                    fill={isInitial ? '#eff6ff' : '#ffffff'}
                                    stroke={isInitial ? '#2563eb' : '#334155'}
                                    strokeWidth={isInitial ? '2.5' : '2'}
                                />

                                {/* Double Circle for Accepting/Final States */}
                                {isFinal && (
                                    <circle
                                        cx={coord.x}
                                        cy={coord.y}
                                        r={nodeRadius - 5}
                                        fill="none"
                                        stroke={isInitial ? '#2563eb' : '#334155'}
                                        strokeWidth="1.8"
                                    />
                                )}

                                {/* State Name Label */}
                                <text
                                    x={coord.x}
                                    y={coord.y + 5}
                                    textAnchor="middle"
                                    fill="#0f172a"
                                    fontSize="13"
                                    fontWeight="bold"
                                    fontFamily="monospace"
                                >
                                    {st}
                                </text>
                            </g>
                        );
                    })}

                    {/* Helper note when transitions are empty */}
                    {transitions.length === 0 && (
                        <text
                            x={svgWidth / 2}
                            y={svgHeight - 16}
                            textAnchor="middle"
                            fill="#94a3b8"
                            fontSize="11"
                            fontStyle="italic"
                        >
                            (Diagram canvas ready — add transitions in the table below to draw graph)
                        </text>
                    )}
                </svg>
            </div>

            {/* Bottom Legend */}
            <div className="d-flex justify-content-center align-items-center gap-3 pt-1 text-muted small" style={{ fontSize: '11px' }}>
                <span className="d-inline-flex align-items-center gap-1">
                    <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', border: '1.5px solid #334155' }}></span>
                    Normal State
                </span>
                <span className="d-inline-flex align-items-center gap-1">
                    <span style={{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', border: '1.5px solid #334155', padding: '1px' }}>
                        <span style={{ display: 'block', width: '6px', height: '6px', borderRadius: '50%', border: '1.5px solid #334155' }}></span>
                    </span>
                    Accepting State (Double Circle)
                </span>
                <span className="d-inline-flex align-items-center gap-1">
                    <span className="text-success fw-bold">▶ Start</span>
                    Initial State
                </span>
                <span className="d-inline-flex align-items-center gap-1">
                    <span className="text-primary fw-bold">⟶ σ</span>
                    Transition Arc
                </span>
            </div>
        </div>
    );
};

export default AutomataDiagramViewer;

