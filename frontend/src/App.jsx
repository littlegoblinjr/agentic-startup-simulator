import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
    Rocket,
    Terminal,
    BarChart3,
    Cpu,
    DollarSign,
    CheckCircle2,
    Search,
    History,
    LayoutDashboard,
    Zap,
    ShieldCheck,
    ChevronRight,
    UserCircle2,
    PieChart,
    LineChart,
    Bot,
    Activity,
    Coins,
    Target,
    RefreshCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import * as api from './services/api';

const App = () => {
    const [idea, setIdea] = useState('');
    const [activeRunId, setActiveRunId] = useState(null);
    const [runStatus, setRunStatus] = useState(null);
    const [logs, setLogs] = useState([]);
    const [runs, setRuns] = useState([]);
    const [view, setView] = useState('dashboard'); // 'dashboard', 'monitor', 'results'
    const logEndRef = useRef(null);
    const [intelModal, setIntelModal] = useState(null);
    const [selectedCard, setSelectedCard] = useState(null);
    const [error, setError] = useState(null);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [refinementFeedback, setRefinementFeedback] = useState("");
    const [expandedRuns, setExpandedRuns] = useState(new Set());

    const safeDate = (dateStr) => {
        const d = new Date(dateStr);
        return isNaN(d.getTime()) ? null : d;
    };

    const intelData = {
        market: {
            title: "Market Validation Engine",
            icon: <BarChart3 />,
            desc: "Our neural agents trigger real-time search queries using the Tavily API to scour the current market landscape. We analyze competitors, customer demand, and emerging trends in India and globally, ensuring your idea isn't built in a vacuum.",
            stats: ["Real-time Tavily Search", "Competitor Benchmarking", "Sentiment Analysis"]
        },
        founder: {
            title: "AI Co-Founder Loop",
            icon: <Bot />,
            desc: "The simulation isn't just a linear process. Our 'Synthesis Agent' acts as a critical co-founder, cross-referencing market data with your technical stack and financial projections to find hidden contradictions and gaps.",
            stats: ["Recursive Synthesis", "Constraint Matching", "Risk Identification"]
        },
        finance: {
            title: "Neural Financial Modeling",
            icon: <LineChart />,
            desc: "We simulate tiered subscription models, CAC/LTV ratios, and operational overheads based on realistic technical infrastructure costs. The result is a break-even projection that's grounded in data, not hope.",
            stats: ["Benchmark Projections", "Unit Economics", "Opex Simulation"]
        },
        growth: {
            title: "Strategic Growth Roadmap",
            icon: <Zap />,
            desc: "Beyond the numbers, we generate a multi-phase implementation plan. This includes specific go-to-market tactics, technical scaling milestones, and risk mitigation strategies tailored to your specific startup niche.",
            stats: ["Multi-Phase Milestones", "GTM Strategy", "Risk Mitigation"]
        }
    };

    useEffect(() => {
        loadRuns();
    }, []);

    useEffect(() => {
        let interval;
        if (activeRunId && (!runStatus || runStatus.status === 'running' || runStatus.status === 'pending')) {
            interval = setInterval(async () => {
                try {
                    const status = await api.getStatus(activeRunId);
                    setRunStatus(status);
                    const logData = await api.getLogs(activeRunId);
                    setLogs(logData.events || []);

                    if (status.status === 'completed') {
                        clearInterval(interval);
                        // Only auto-switch to results if we are currently looking at the logs
                        setView(prev => prev === 'monitor' ? 'results' : prev);
                        loadRuns();
                    }
                } catch (err) {
                    console.error("Polling error:", err);
                }
            }, 2000);
        }
        return () => clearInterval(interval);
    }, [activeRunId, runStatus?.status]); // Only depend on status string, not whole object

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const loadRuns = async () => {
        const data = await api.listRuns();
        setRuns(data);
    };

    const startSimulation = async () => {
        if (!idea.trim()) return;
        setLogs([]);
        setRunStatus({ status: 'pending' });
        setView('monitor');
        try {
            const runId = await api.simulate(idea);
            setActiveRunId(runId);
        } catch (err) {
            const msg = err.response?.data?.detail || "Simulation failed to start.";
            setError(msg);
            setView('dashboard');
        }
    };

    const handleRefinement = async () => {
        if (!refinementFeedback.trim()) return;
        const parentId = activeRunId;
        const targetIdea = runStatus.results.idea;

        setLogs([]);
        setRunStatus({ status: 'pending' });
        setView('monitor');
        setRefinementFeedback("");

        try {
            const runId = await api.simulate(targetIdea, parentId, refinementFeedback);
            setActiveRunId(runId);
            // Wait for first log to appear or timeout
            setTimeout(() => {
                const monitorEl = document.getElementById('monitor-logs');
                if (monitorEl) monitorEl.scrollTop = 0;
            }, 500);
        } catch (err) {
            const msg = err.response?.data?.detail || "Refinement failed.";
            setError(msg);
            setView('results');
        }
    };

    const selectRun = async (runId) => {
        try {
            setActiveRunId(runId);
            const status = await api.getStatus(runId);
            setRunStatus(status);

            const logData = await api.getLogs(runId);
            setLogs(logData.events || []);

            // If it's completed, show results. If running/pending/failed, show monitor.
            if (status.status === 'completed') {
                setView('results');
            } else {
                setView('monitor');
            }
        } catch (err) {
            console.error("Error selecting run:", err);
            // Fallback to monitor to see logs
            setView('monitor');
        }
    };

    // Calculate token metrics
    // Group runs by their root parent
    const groupedRuns = useMemo(() => {
        if (!Array.isArray(runs)) return [];
        const rootRuns = runs.filter(r => !r.parent_run_id);
        const iterations = runs.filter(r => r.parent_run_id);

        return rootRuns.map(root => {
            const visited = new Set();
            const findDescendants = (parentId) => {
                if (visited.has(parentId)) return [];
                visited.add(parentId);
                const children = iterations.filter(r => r.parent_run_id === parentId);
                let all = [...children];
                children.forEach(child => {
                    all = [...all, ...findDescendants(child.run_id)];
                });
                return all;
            };

            const descendants = findDescendants(root.run_id);
            const sortedDescendants = descendants.sort((a, b) => (safeDate(a.created_at) || 0) - (safeDate(b.created_at) || 0));

            return {
                ...root,
                iteration: 1, // Root is always v1
                iterations: sortedDescendants.map((it, idx) => ({
                    ...it,
                    iteration: idx + 2 // descendants start at v2
                }))
            };
        });
    }, [runs]);

    const activeIteration = useMemo(() => {
        if (!activeRunId || !groupedRuns.length) return 1;
        for (const root of groupedRuns) {
            if (root.run_id === activeRunId) return 1;
            const it = root.iterations.find(i => i.run_id === activeRunId);
            if (it) return it.iteration;
        }
        return 1;
    }, [activeRunId, groupedRuns]);

    const parentRun = useMemo(() => {
        if (!activeRunId || !Array.isArray(runs)) return null;
        const currentRun = runs.find(r => r.run_id === activeRunId);
        if (!currentRun || !currentRun.parent_run_id) return null;
        const parent = runs.find(r => r.run_id === currentRun.parent_run_id);
        if (!parent) return null;

        let results = parent.results;
        if (typeof results === 'string') {
            try { results = JSON.parse(results); } catch (e) { return null; }
        }
        let context = results?.final_context;
        if (typeof context === 'string') {
            try { context = JSON.parse(context); } catch (e) { return null; }
        }
        return { ...parent, context };
    }, [activeRunId, runs]);

    // Maps context keys to their originating agent for modification tracking
    const keyToAgentMap = {
        'market_analysis': 'market_agent',
        'tech_analysis': 'tech_agent',
        'financial_projections': 'finance_agent',
        'growth_roadmap': 'synthesis_agent',
        'risk_mitigation': 'synthesis_agent',
        'pitch_narrative': 'pitch_agent'
    };

    const checkIfModified = (key, currentContext) => {
        // If it's the very first run, everything is 'modified' (new)
        if (!parentRun) return true;

        // Ensure plan is available
        const planRaw = runStatus?.results?.plan;
        let p = planRaw;
        if (typeof p === 'string') {
            try { p = JSON.parse(p); } catch (e) { p = null; }
        }

        if (!p) return true; // Default to modified if plan is missing

        const skipped = p.skipped_agents || [];
        const responsibleAgent = keyToAgentMap[key];

        // If the agent responsible for this key was skipped, it's STABLE (false)
        if (responsibleAgent && skipped.includes(responsibleAgent)) {
            return false;
        }

        // Otherwise, it ran, so it's MODIFIED (true)
        return true;
    };



    const toggleExpand = (e, runId) => {
        e.stopPropagation();
        const next = new Set(expandedRuns);
        if (next.has(runId)) next.delete(runId);
        else next.add(runId);
        setExpandedRuns(next);
    };

    const tokenMetrics = useMemo(() => {
        if (!Array.isArray(logs)) return { totalTokens: 0, avgTokensPerRequest: 0, density: 0 };
        const totalTokens = logs.reduce((sum, log) => sum + (log.usage?.total_tokens || 0), 0);
        const avgTokensPerRequest = logs.length > 0 ? Math.round(totalTokens / logs.filter(l => l.usage).length) || 0 : 0;
        // Mock "Capability Density" calculation: tokens / uniqueness of thoughts (highly stylized)
        const density = totalTokens > 0 ? (logs.length * 100 / (totalTokens / 1000)).toFixed(1) : 0;
        return { totalTokens, avgTokensPerRequest, density };
    }, [logs]);

    return (
        <div className="flex flex-col md:flex-row h-screen bg-background font-sans text-slate-300 relative overflow-hidden">
            {/* Mobile Header */}
            <header className="md:hidden flex items-center justify-between p-4 bg-[#05070a] border-b border-white/5 z-50">
                <div className="flex items-center gap-2">
                    <Rocket className="text-primary w-6 h-6 rotate-45" />
                    <h1 className="text-sm font-black tracking-tighter text-white uppercase italic">Launchpad AI</h1>
                </div>
                <button
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    className="p-2 text-slate-400 hover:text-white transition-colors"
                >
                    <Terminal size={20} />
                </button>
            </header>
            {/* Intel Modal */}
            <AnimatePresence>
                {intelModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] flex items-center justify-center p-10 bg-black/80 backdrop-blur-xl"
                        onClick={() => setIntelModal(null)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.9, y: 20 }}
                            className="glass-card max-w-2xl w-full p-8 md:p-16 rounded-[32px] md:rounded-[48px] border-white/10 shadow-2xl relative bg-[#0d1117] text-left"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="absolute top-10 right-10">
                                <button onClick={() => setIntelModal(null)} className="text-slate-500 hover:text-white transition-colors p-2">
                                    <Terminal size={24} />
                                </button>
                            </div>
                            <div className="flex items-center gap-6 mb-12">
                                <div className="bg-primary/20 p-5 rounded-3xl text-primary shadow-neon-indigo">
                                    {React.cloneElement(intelData[intelModal].icon, { size: 32 })}
                                </div>
                                <div>
                                    <span className="text-[10px] font-black uppercase tracking-[0.4em] text-primary italic mb-2 block">Neural Intel Briefing</span>
                                    <h3 className="text-3xl font-black text-white uppercase italic tracking-tighter">{intelData[intelModal].title}</h3>
                                </div>
                            </div>
                            <p className="text-lg text-slate-400 leading-relaxed mb-12">
                                {intelData[intelModal].desc}
                            </p>
                            <div className="grid grid-cols-1 gap-4">
                                {intelData[intelModal].stats.map((stat, i) => (
                                    <div key={i} className="flex items-center gap-4 text-xs font-black text-primary uppercase tracking-[0.1em] bg-primary/5 p-4 rounded-2xl border border-primary/10 italic">
                                        <Zap size={14} fill="currentColor" /> {stat}
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Results Detail Modal */}
            <AnimatePresence>
                {selectedCard && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] flex items-center justify-center p-10 bg-black/80 backdrop-blur-xl"
                        onClick={() => setSelectedCard(null)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.9, y: 20 }}
                            className="glass-card max-w-4xl w-full p-8 md:p-16 rounded-[32px] md:rounded-[48px] border-white/10 shadow-2xl relative bg-[#0b0e14] text-left max-h-[85vh] overflow-y-auto custom-scrollbar"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="absolute top-10 right-10">
                                <button onClick={() => setSelectedCard(null)} className="text-slate-500 hover:text-white transition-colors p-2 bg-white/5 rounded-full">
                                    <Terminal size={24} />
                                </button>
                            </div>

                            <div className="flex items-center gap-6 mb-12">
                                <div className="bg-primary/20 p-5 rounded-3xl text-primary shadow-neon-indigo">
                                    <BarChart3 size={32} />
                                </div>
                                <div>
                                    <span className="text-[10px] font-black uppercase tracking-[0.4em] text-primary italic mb-2 block">Agentic Intel Insight</span>
                                    <h3 className="text-4xl font-black text-white uppercase italic tracking-tighter">{selectedCard.title}</h3>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 gap-12">
                                {Object.entries(selectedCard.content).map(([key, val], i) => (
                                    <div key={i} className="space-y-4 border-l border-white/5 pl-8">
                                        <div className="flex items-center gap-3">
                                            <div className="w-1.5 h-1.5 rounded-full bg-primary shadow-neon-indigo" />
                                            <span className="text-xs font-black uppercase tracking-[0.3em] text-slate-500">{key.replace('_', ' ')}</span>
                                        </div>
                                        <div className="text-lg text-slate-300 font-medium leading-relaxed italic">
                                            {Array.isArray(val) ? (
                                                <div className="flex flex-wrap gap-3 mt-2">
                                                    {val.map((item, idx) => (
                                                        <span key={idx} className="bg-primary/10 text-primary border border-primary/20 px-4 py-2 rounded-xl text-sm font-black italic uppercase tracking-wider">
                                                            {item}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : (
                                                <p className="whitespace-pre-wrap">{val}</p>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
            {/* Sidebar (Desktop & Mobile Drawer) */}
            <aside className={`
                fixed md:static inset-0 z-40 w-full md:w-80 bg-[#05070a] border-r border-white/5 flex flex-col p-8 transition-transform duration-300 ease-in-out
                ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
            `}>
                <div className="hidden md:flex items-center gap-3 mb-12 px-2">
                    <Rocket className="text-primary w-8 h-8 rotate-45" />
                    <h1 className="text-xl font-black tracking-tighter text-white uppercase italic">Launchpad AI</h1>
                </div>

                <nav className="space-y-3 mb-12">
                    <button
                        onClick={() => { setView('dashboard'); setIsMobileMenuOpen(false); }}
                        className={`w-full flex items-center gap-4 px-5 py-3.5 rounded-2xl transition-all ${view === 'dashboard' ? 'bg-primary/10 text-primary border border-primary/20' : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'}`}
                    >
                        <LayoutDashboard size={20} />
                        <span className="font-bold uppercase text-xs tracking-widest">Console</span>
                    </button>

                    {activeRunId && (
                        <button
                            onClick={() => { setView(runStatus?.status === 'completed' ? 'results' : 'monitor'); setIsMobileMenuOpen(false); }}
                            className={`w-full flex items-center gap-4 px-5 py-3.5 rounded-2xl transition-all ${view !== 'dashboard' ? 'bg-accent/10 text-accent border border-accent/20' : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'}`}
                        >
                            <Activity size={20} />
                            <span className="font-bold uppercase text-xs tracking-widest">Live Uplink</span>
                        </button>
                    )}
                </nav>

                <div className="flex-1 overflow-hidden flex flex-col">
                    <div className="flex items-center justify-between mb-6 px-2">
                        <h2 className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em] flex items-center gap-2">
                            <History size={14} />
                            Simulation History
                        </h2>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-4 pr-3 custom-scrollbar">
                        {groupedRuns.map(root => (
                            <div key={root.run_id} className="space-y-2">
                                <div className="relative group">
                                    <button
                                        onClick={() => selectRun(root.run_id)}
                                        className={`w-full text-left p-5 rounded-2xl glass-card transition-all group relative border-white/5 ${activeRunId === root.run_id ? 'border-primary/40 bg-primary/5' : 'hover:border-primary/40'}`}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <p className="text-xs font-bold text-slate-300 line-clamp-2 mb-3 leading-relaxed flex-1">{root.idea}</p>
                                            {root.iterations.length > 0 && (
                                                <button
                                                    onClick={(e) => toggleExpand(e, root.run_id)}
                                                    className={`mt-0.5 p-1 rounded-lg hover:bg-white/10 transition-transform ${expandedRuns.has(root.run_id) ? 'rotate-90' : ''}`}
                                                >
                                                    <ChevronRight size={14} className="text-slate-500" />
                                                </button>
                                            )}
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <span className="text-[9px] font-mono text-slate-600 uppercase">{safeDate(root.created_at)?.toLocaleDateString() || "TBD"}</span>
                                                <span className="text-[8px] font-black text-slate-700 uppercase bg-white/5 px-1.5 py-0.5 rounded">v1</span>
                                            </div>
                                            {root.score && (
                                                <span className="text-[9px] font-black text-primary border border-primary/30 px-2 py-0.5 rounded-full bg-primary/5 uppercase">
                                                    {root.score} PTs
                                                </span>
                                            )}
                                        </div>
                                    </button>
                                </div>

                                {/* Iterations */}
                                <AnimatePresence>
                                    {(expandedRuns.has(root.run_id) || activeRunId === root.run_id || root.iterations.some(it => it.run_id === activeRunId)) && root.iterations.map((it, idx) => (
                                        <motion.div
                                            key={it.run_id}
                                            initial={{ opacity: 0, x: -10, height: 0 }}
                                            animate={{ opacity: 1, x: 0, height: 'auto' }}
                                            exit={{ opacity: 0, x: -10, height: 0 }}
                                            className="ml-6 relative"
                                        >
                                            <div className="absolute -left-3 top-0 bottom-0 w-px bg-white/10" />
                                            <button
                                                onClick={() => selectRun(it.run_id)}
                                                className={`w-full text-left p-4 rounded-xl glass-card transition-all relative border-white/5 ${activeRunId === it.run_id ? 'border-primary/40 bg-primary/5' : 'hover:border-primary/40'}`}
                                            >
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-[8px] font-black text-primary/60 uppercase">Iteration v{it.iteration}</span>
                                                        <span className="text-[7px] font-mono text-slate-700">{safeDate(it.created_at)?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) || "TBD"}</span>
                                                    </div>
                                                    {it.score && (
                                                        <span className="text-[7px] font-black text-primary/60">{it.score} PTs</span>
                                                    )}
                                                </div>
                                                <p className="text-[10px] text-slate-400 line-clamp-1 italic">
                                                    {it.feedback || "Refinement run"}
                                                </p>
                                            </button>
                                        </motion.div>
                                    ))}
                                </AnimatePresence>
                            </div>
                        ))}
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto relative z-10 custom-scrollbar">
                <div className="max-w-6xl mx-auto px-6 md:px-16 py-8 md:py-16">
                    <AnimatePresence mode="wait">
                        {view === 'dashboard' && (
                            <motion.section
                                key="dashboard"
                                initial={{ opacity: 0, scale: 0.98 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 1.02 }}
                                className="flex flex-col items-center text-center space-y-20 pt-10"
                            >
                                <header className="space-y-6 max-w-3xl">
                                    <motion.div
                                        initial={{ y: 10, opacity: 0 }}
                                        animate={{ y: 0, opacity: 1 }}
                                        className="inline-block"
                                    >
                                        <Rocket className="w-16 h-16 text-primary mx-auto mb-6 drop-shadow-[0_0_15px_rgba(79,70,229,0.5)]" />
                                    </motion.div>
                                    <h2 className="text-4xl md:text-6xl font-black text-white leading-none tracking-tighter uppercase italic">
                                        Simulate Your <br className="hidden md:block" />
                                        <span className="text-primary italic">Startup Success.</span>
                                    </h2>
                                    <p className="text-slate-500 text-sm md:text-lg font-medium tracking-tight">
                                        Validate, test, and grow your startup ideas with <br className="hidden md:block" />advanced AI simulations.
                                    </p>
                                </header>

                                <div className="relative group w-full max-w-4xl">
                                    <div className="absolute -inset-1 bg-gradient-to-r from-primary/50 to-accent/50 rounded-[32px] md:rounded-[40px] blur opacity-25 group-focus-within:opacity-50 transition duration-1000"></div>
                                    <div className="relative flex flex-col md:flex-row items-center bg-[#0d1117] border border-white/10 rounded-[28px] md:rounded-[32px] p-3 md:p-4 shadow-2xl backdrop-blur-xl">
                                        <div className="hidden md:flex items-center gap-6 px-6 border-r border-white/5">
                                            <Rocket className="text-primary w-6 h-6 rotate-45" />
                                        </div>
                                        <input
                                            type="text"
                                            value={idea}
                                            onChange={(e) => {
                                                setIdea(e.target.value);
                                                if (error) setError(null);
                                            }}
                                            maxLength={1000}
                                            placeholder="Enter your startup idea..."
                                            className="w-full md:flex-1 bg-transparent border-none py-4 md:py-6 px-4 md:px-4 text-white text-base md:text-lg focus:outline-none placeholder:text-slate-600"
                                        />
                                        <button
                                            onClick={startSimulation}
                                            className="w-full md:w-auto bg-primary hover:bg-primary/90 text-white font-black text-[10px] md:text-xs tracking-[0.2em] px-6 md:px-8 py-4 md:py-5 rounded-[18px] md:rounded-[22px] transition-all flex items-center justify-center gap-3 uppercase italic shadow-lg shadow-primary/20"
                                        >
                                            Generate Simulation <ChevronRight size={16} />
                                        </button>
                                    </div>
                                    {error && (
                                        <motion.div
                                            initial={{ opacity: 0, y: -10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className="absolute -bottom-10 left-8 text-red-500 text-[10px] font-black uppercase tracking-widest flex items-center gap-2"
                                        >
                                            <Terminal size={12} /> {error}
                                        </motion.div>
                                    )}
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-8 w-full max-w-4xl">
                                    <MockupCard title="Market Validation" icon={<BarChart3 />} desc="Simulate current market conditions to test your core value proposition." onClick={() => setIntelModal('market')} />
                                    <MockupCard title="AI Co-Founder" icon={<Bot />} desc="AI agents refine your strategy with expert consistency checks." onClick={() => setIntelModal('founder')} />
                                    <MockupCard title="Financial Modeling" icon={<LineChart />} desc="Analytics, financial modeling, and realistic growth projections." onClick={() => setIntelModal('finance')} />
                                    <MockupCard title="Growth Strategy" icon={<Zap />} desc="Multi-phase roadmaps and risk mitigation tactics." onClick={() => setIntelModal('growth')} />
                                </div>
                            </motion.section>
                        )}

                        {view === 'monitor' && (
                            <motion.section
                                key="monitor"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="space-y-10"
                            >
                                <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-white/5 pb-8 gap-6">
                                    <header>
                                        <div className="flex items-center gap-3 text-primary mb-3">
                                            <Zap size={18} fill="currentColor" />
                                            <span className="text-[10px] font-black uppercase tracking-[0.4em] italic">Telemetry Uplink Active</span>
                                        </div>
                                        <h2 className="text-2xl md:text-4xl font-black text-white uppercase italic tracking-tighter">Processing Neural Loop...</h2>
                                    </header>

                                    <div className="flex flex-col sm:flex-row items-center gap-4">
                                        <div className="glass-card px-4 md:px-6 py-3 rounded-2xl border-white/5 flex items-center gap-6 md:gap-8">
                                            <div className="text-center">
                                                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block mb-1">Metabolism</span>
                                                <span className="text-xs font-black text-primary font-mono">{tokenMetrics.totalTokens}<span className="text-[10px] ml-1">TK</span></span>
                                            </div>
                                            <div className="w-px h-8 bg-white/5" />
                                            <div className="text-center text-primary">
                                                <Activity className="animate-pulse" size={18} />
                                            </div>
                                        </div>
                                        <div className="flex -space-x-3">
                                            <div className="w-10 h-10 rounded-full border-4 border-[#05070a] bg-primary/20 flex items-center justify-center text-primary">
                                                <Bot size={16} />
                                            </div>
                                            <div className="w-10 h-10 rounded-full border-4 border-[#05070a] bg-accent/20 flex items-center justify-center text-accent">
                                                <Activity size={16} />
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
                                    <MetricMiniCard icon={<Zap size={16} />} label="Agent density" value={`${tokenMetrics.density}%`} color="text-yellow-500" />
                                    <MetricMiniCard icon={<Coins size={16} />} label="Cost / Query" value={`$${(tokenMetrics.totalTokens * 0.000005).toFixed(4)}`} color="text-emerald-500" />
                                    <MetricMiniCard icon={<Activity size={16} />} label="Avg Tokens" value={tokenMetrics.avgTokensPerRequest} color="text-indigo-500" />
                                    <MetricMiniCard icon={<Target size={16} />} label="Directives" value={logs.length} color="text-primary" />
                                </div>

                                <div
                                    id="monitor-logs"
                                    className="flex-1 bg-[#05070a] rounded-3xl border border-white/5 p-6 md:p-10 font-mono text-[10px] md:text-xs overflow-y-auto custom-scrollbar min-h-[50vh] max-h-[70vh] relative shadow-inner"
                                >
                                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
                                    {logs.length === 0 && (
                                        <div className="flex flex-col items-center justify-center h-full text-slate-600 animate-pulse py-20">
                                            <Activity size={32} className="mb-4" />
                                            <p className="uppercase tracking-[0.3em] font-black italic">Initiating Neural Link...</p>
                                            <p className="text-[8px] mt-2 opacity-50">Planning optimized agent trajectories</p>
                                        </div>
                                    )}
                                    <div className="space-y-4">
                                        {logs.map((log, i) => (
                                            <div key={i} className="flex gap-4 group">
                                                <span className="text-slate-800 shrink-0 font-bold">[{safeDate(log.timestamp)?.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) || "00:00:00"}]</span>
                                                <span className="text-primary font-black uppercase tracking-tighter shrink-0 w-24">▸ {log.agent_type}</span>
                                                <div className="space-y-1">
                                                    <span className="text-slate-200 block font-bold tracking-tight">{log.event_type}</span>
                                                    {log.data && <p className="text-slate-500 italic max-w-2xl leading-relaxed">{JSON.stringify(log.data).slice(0, 300)}</p>}
                                                </div>
                                            </div>
                                        ))}
                                        <div ref={logEndRef} />
                                    </div>
                                </div>
                            </motion.section>
                        )}

                        {view === 'results' && (
                            <motion.section
                                key="results"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="space-y-16"
                            >
                                {(() => {
                                    // CRASH GUARD: Attempt to recover results/context if it's stringified
                                    let results = runStatus?.results;
                                    if (typeof results === 'string') {
                                        try { results = JSON.parse(results); } catch (e) { }
                                    }
                                    let context = results?.final_context;
                                    if (typeof context === 'string') {
                                        try { context = JSON.parse(context); } catch (e) { }
                                    }

                                    if (!context || typeof context !== 'object') {
                                        return (
                                            <div className="glass-card p-12 rounded-[40px] bg-rose-500/5 border border-rose-500/20 text-center space-y-6">
                                                <div className="bg-rose-500/20 p-4 rounded-full w-fit mx-auto text-rose-500"><Terminal size={32} /></div>
                                                <h3 className="text-2xl font-black text-white uppercase italic">Neural Data Mismatch</h3>
                                                <p className="text-slate-400 max-w-md mx-auto italic">The simulation completed, but the result payload is malformed or hidden. Our agents are currently re-indexing the neural context.</p>
                                                <div className="pt-6">
                                                    <button onClick={() => setView('monitor')} className="text-[10px] font-black text-primary uppercase tracking-[0.3em] border-b border-primary/30 pb-1">Return to Telemetry Uplink</button>
                                                </div>
                                            </div>
                                        );
                                    }

                                    return (
                                        <>
                                            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 border-b border-white/5 pb-10">
                                                <div className="text-left">
                                                    <div className="flex items-center gap-3 text-emerald-500 mb-4">
                                                        <ShieldCheck size={18} fill="currentColor" />
                                                        <span className="text-[10px] font-black uppercase tracking-[0.4em] italic">Simulation Payload Verified</span>
                                                    </div>
                                                    <h2 className="text-4xl md:text-5xl font-black text-white uppercase italic tracking-tighter leading-none mb-3">Analysis Compiled.</h2>
                                                    <p className="text-slate-500 text-sm md:text-lg font-medium italic">Your startup trajectory has been mapped across 6 neural dimensions.</p>
                                                </div>

                                                <div className="flex flex-col sm:flex-row items-center gap-6">
                                                    <div className="glass-card px-4 md:px-6 py-3 rounded-2xl border-white/5 flex items-center gap-6 md:gap-8 bg-white/5">
                                                        <div className="text-center">
                                                            <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block mb-1 italic">Neural Cost</span>
                                                            <span className="text-xs font-black text-emerald-500 font-mono">${(tokenMetrics.totalTokens * 0.000005).toFixed(4)}</span>
                                                        </div>
                                                        <div className="w-px h-8 bg-white/5" />
                                                        <div className="text-center">
                                                            <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block mb-1 italic">Metabolism</span>
                                                            <span className="text-xs font-black text-primary font-mono">{tokenMetrics.totalTokens}<span className="text-[10px] ml-1">TK</span></span>
                                                        </div>
                                                    </div>
                                                    <div className="bg-primary/20 px-8 py-4 rounded-[28px] border border-primary/30 shadow-neon-indigo">
                                                        <span className="text-[10px] font-black text-primary uppercase tracking-[0.4em] block mb-1 italic text-center">Readiness</span>
                                                        <span className="text-5xl font-black text-white italic tracking-tighter">
                                                            {context?.evaluation_scorecard?.total_score ?? "N/A"}
                                                            <span className="text-lg ml-1 opacity-50">/100</span>
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
                                                <ResultCard
                                                    title="Market Intel"
                                                    content={context?.market_analysis}
                                                    onClick={setSelectedCard}
                                                    version={checkIfModified('market_analysis', context) ? activeIteration : (parentRun?.iteration || 1)}
                                                    isModified={checkIfModified('market_analysis', context)}
                                                    hasHistory={!!parentRun}
                                                />
                                                <ResultCard
                                                    title="Tech Blueprint"
                                                    content={context?.tech_analysis}
                                                    onClick={setSelectedCard}
                                                    version={checkIfModified('tech_analysis', context) ? activeIteration : (parentRun?.iteration || 1)}
                                                    isModified={checkIfModified('tech_analysis', context)}
                                                    hasHistory={!!parentRun}
                                                />
                                                <ResultCard
                                                    title="Financial Core"
                                                    content={context?.financial_projections}
                                                    onClick={setSelectedCard}
                                                    version={checkIfModified('financial_projections', context) ? activeIteration : (parentRun?.iteration || 1)}
                                                    isModified={checkIfModified('financial_projections', context)}
                                                    hasHistory={!!parentRun}
                                                />
                                            </div>

                                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8 auto-rows-fr">
                                                <div className={`glass-card p-8 rounded-[32px] bg-[#0d1117]/80 border-white/5 space-y-8 flex flex-col hover:border-primary/30 transition-all relative overflow-hidden ${checkIfModified('growth_roadmap', context) || checkIfModified('risk_mitigation', context) ? 'ring-1 ring-primary/20' : ''}`}>
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-3">
                                                            <div className="bg-primary/20 p-2 rounded-lg text-primary shadow-neon-indigo"><Rocket size={16} /></div>
                                                            <h4 className="font-black text-[10px] uppercase tracking-[0.4em] text-primary italic">Execution & Risk Strategy</h4>
                                                            <div className="bg-white/5 px-2 py-0.5 rounded text-[8px] font-black text-slate-500 uppercase tracking-widest border border-white/5">v{checkIfModified('growth_roadmap', context) || checkIfModified('risk_mitigation', context) ? activeIteration : (parentRun?.iteration || 1)}</div>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            {!!parentRun && (checkIfModified('growth_roadmap', context) || checkIfModified('risk_mitigation', context)) && (
                                                                <span className="bg-primary text-white text-[8px] font-black px-2 py-1 rounded tracking-[0.2em] shadow-lg shadow-primary/20 animate-pulse">MODIFIED</span>
                                                            )}
                                                            {!!parentRun && !(checkIfModified('growth_roadmap', context) || checkIfModified('risk_mitigation', context)) && (
                                                                <span className="bg-white/5 text-slate-500 text-[8px] font-black px-2 py-1 rounded tracking-[0.2em] border border-white/5 uppercase">Stable</span>
                                                            )}
                                                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                                            <span className="text-[8px] font-black text-slate-600 uppercase tracking-widest">Neural Sync Active</span>
                                                        </div>
                                                    </div>

                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 flex-1">
                                                        <div className="space-y-4">
                                                            <div className="flex items-center justify-between border-b border-white/5 pb-2">
                                                                <span className="text-[9px] font-black text-white uppercase tracking-widest block italic">Strategic Roadmap</span>
                                                                {checkIfModified('growth_roadmap', context) && <span className="text-[7px] font-black text-primary uppercase tracking-widest bg-primary/10 px-1.5 rounded">NEW</span>}
                                                            </div>
                                                            <p className="text-slate-400 text-xs leading-relaxed italic"><span className="text-primary font-black uppercase text-[9px] mr-2">Core</span> {context?.growth_roadmap?.strategy ?? "Trajectory Pending..."}</p>
                                                            <ul className="space-y-2">
                                                                {Array.isArray(context?.growth_roadmap?.recommendations) ? context.growth_roadmap.recommendations.slice(0, 3).map((r, i) => (
                                                                    <li key={i} className="flex items-start gap-2 text-[10px] text-slate-500 italic">
                                                                        <span className="w-1 h-1 rounded-full bg-emerald-500 mt-1.5 shrink-0" /> {r}
                                                                    </li>
                                                                )) : (
                                                                    <li className="text-[10px] text-slate-500 italic">{context?.growth_roadmap?.recommendations || "No recommendations found."}</li>
                                                                )}
                                                            </ul>
                                                        </div>
                                                        <div className="space-y-4">
                                                            <div className="flex items-center justify-between border-b border-white/5 pb-2">
                                                                <span className="text-[9px] font-black text-rose-500 uppercase tracking-widest block italic">Risk Mitigation</span>
                                                                {checkIfModified('risk_mitigation', context) && <span className="text-[7px] font-black text-rose-500 uppercase tracking-widest bg-rose-500/10 px-1.5 rounded">NEW</span>}
                                                            </div>
                                                            <ul className="space-y-3">
                                                                {Array.isArray(context?.risk_mitigation?.key_risks) ? context.risk_mitigation.key_risks.slice(0, 3).map((r, i) => (
                                                                    <li key={i} className="flex items-start gap-2 text-[10px] text-slate-400 italic font-medium">
                                                                        <span className="w-1 h-1 rounded-full bg-rose-500 mt-1.5 shrink-0" /> {r}
                                                                    </li>
                                                                )) : (
                                                                    <li className="text-[10px] text-slate-400 italic font-medium">{context?.risk_mitigation?.key_risks || "No major risks identified."}</li>
                                                                )}
                                                            </ul>
                                                            <div className="pt-2 text-[9px] text-yellow-500/80 font-black uppercase tracking-widest leading-relaxed">
                                                                {Array.isArray(context?.risk_mitigation?.gaps) ? context.risk_mitigation.gaps[0] : (context?.risk_mitigation?.gaps || "Structural analysis in progress...")}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div className={`glass-card p-8 rounded-[32px] bg-primary/5 border border-primary/20 space-y-6 relative overflow-hidden flex flex-col hover:bg-primary/10 transition-all ${checkIfModified('pitch_deck', context) ? 'ring-1 ring-primary/40' : ''}`}>
                                                    <div className="absolute top-0 right-0 w-24 h-24 bg-primary/10 blur-[40px] rounded-full" />
                                                    <div className="flex items-center justify-between relative z-10">
                                                        <div className="flex items-center gap-3">
                                                            <h4 className="font-black text-[10px] uppercase tracking-[0.4em] text-primary italic">Pitch Narrative</h4>
                                                            <div className="bg-primary/10 px-2 py-0.5 rounded text-[8px] font-black text-primary uppercase tracking-widest border border-primary/20">v{activeIteration}</div>
                                                        </div>
                                                        {!!parentRun && checkIfModified('pitch_deck', context) && (
                                                            <span className="bg-primary text-white text-[8px] font-black px-2 py-1 rounded tracking-[0.2em] shadow-lg shadow-primary/20 animate-pulse">MODIFIED</span>
                                                        )}
                                                        {!!parentRun && !checkIfModified('pitch_deck', context) && (
                                                            <span className="bg-white/5 text-slate-500 text-[8px] font-black px-2 py-1 rounded tracking-[0.2em] border border-white/5 uppercase">Stable</span>
                                                        )}
                                                    </div>
                                                    <div className="space-y-6 flex-1">
                                                        <PitchSection title="The Vision" highlight content={context?.pitch_deck?.vision_statement} />
                                                        <PitchSection title="Core Mission" content={context?.pitch_deck?.solution_summary} />
                                                    </div>
                                                    <button
                                                        onClick={() => setSelectedCard({ title: "Pitch Narrative", content: context?.pitch_deck })}
                                                        className="w-full py-3 bg-primary text-white rounded-xl text-[9px] font-black uppercase tracking-[0.3em] italic hover:bg-primary/90 transition-all shadow-lg shadow-primary/20 mt-auto"
                                                    >
                                                        View Full Pitch
                                                    </button>
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8 text-left">
                                                <div className="glass-card p-6 md:p-10 rounded-[32px] md:rounded-[40px] space-y-6 md:space-y-8 bg-[#0d1117]/80 border-white/5">
                                                    <h4 className="font-black text-[10px] md:text-xs uppercase tracking-[0.4em] text-primary italic">Critique Intelligence</h4>
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
                                                        <div>
                                                            <span className="text-[9px] md:text-[10px] font-black text-emerald-500 uppercase tracking-widest block mb-3 md:mb-4 italic">Quality Indicators</span>
                                                            <ul className="space-y-2 md:space-y-3">
                                                                {Array.isArray(context?.evaluation_scorecard?.feedback?.strengths) ? context.evaluation_scorecard.feedback.strengths.map((s, i) => (
                                                                    <li key={i} className="text-[10px] md:text-[11px] text-slate-400 flex items-start gap-3 leading-relaxed">
                                                                        <span className="mt-1.5 w-1 h-1 rounded-full bg-emerald-500 shrink-0" /> {s}
                                                                    </li>
                                                                )) : (
                                                                    <li className="text-[10px] md:text-[11px] text-slate-400 italic">{context?.evaluation_scorecard?.feedback?.strengths || "Strengths analysis pending."}</li>
                                                                )}
                                                            </ul>
                                                        </div>
                                                        <div>
                                                            <span className="text-[9px] md:text-[10px] font-black text-rose-500 uppercase tracking-widest block mb-3 md:mb-4 italic">Optimisation</span>
                                                            <ul className="space-y-2 md:space-y-3">
                                                                {Array.isArray(context?.evaluation_scorecard?.feedback?.weaknesses) ? context.evaluation_scorecard.feedback.weaknesses.map((s, i) => (
                                                                    <li key={i} className="text-[10px] md:text-[11px] text-slate-400 flex items-start gap-3 leading-relaxed">
                                                                        <span className="mt-1.5 w-1 h-1 rounded-full bg-rose-500 shrink-0" /> {s}
                                                                    </li>
                                                                )) : (
                                                                    <li className="text-[10px] md:text-[11px] text-slate-400 italic">{context?.evaluation_scorecard?.feedback?.weaknesses || "No critical weaknesses found."}</li>
                                                                )}
                                                            </ul>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="bg-primary/5 border border-primary/20 p-8 md:p-12 rounded-[32px] md:rounded-[40px] flex flex-col justify-center text-center relative overflow-hidden">
                                                    <div className="absolute top-0 right-0 w-24 md:w-32 h-24 md:h-32 bg-primary/20 blur-[60px] rounded-full" />
                                                    <h4 className="text-[9px] md:text-[10px] font-black uppercase tracking-[0.5em] text-primary mb-6 md:mb-10 italic text-center">Executive Verdict</h4>
                                                    <p className="text-xl md:text-3xl font-black italic text-white leading-tight tracking-tight uppercase text-center">
                                                        "{context?.evaluation_scorecard?.feedback?.investor_verdict ?? "Neural Analysis Pending..."}"
                                                    </p>
                                                </div>
                                            </div>
                                        </>
                                    );
                                })()}

                                <div className="mt-16 pb-40">
                                    <div className="text-left">
                                        <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.4em] mb-4 italic">Neural Pivot Interface</h4>
                                        <p className="text-sm text-slate-400 mb-8 max-w-xl leading-relaxed">
                                            Not satisfied with the current trajectory? Provide feedback to the agent swarm to pivot the business model, tech stack, or financial projections.
                                        </p>
                                    </div>
                                </div>

                                {/* Floating Refinement Input */}
                                <div className="fixed bottom-8 left-1/2 -translate-x-1/2 w-full max-w-4xl px-6 z-30">
                                    <div className="relative group">
                                        <div className="absolute -inset-1 bg-gradient-to-r from-accent/50 to-primary/50 rounded-[28px] blur opacity-25 group-focus-within:opacity-50 transition duration-1000"></div>
                                        <div className="relative bg-[#0d1117] border border-white/10 rounded-[24px] p-2 md:p-3 flex flex-col md:flex-row items-end gap-6 shadow-2xl backdrop-blur-xl">
                                            <textarea
                                                value={refinementFeedback}
                                                onChange={(e) => setRefinementFeedback(e.target.value)}
                                                placeholder="e.g. Pivot to a B2B subscription model with a focus on enterprise security..."
                                                className="w-full bg-transparent border-none text-slate-200 placeholder:text-slate-600 focus:outline-none resize-none h-20 text-sm leading-relaxed p-4"
                                            />
                                            <button
                                                onClick={handleRefinement}
                                                disabled={!refinementFeedback.trim()}
                                                className="w-full md:w-auto bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-black text-[10px] tracking-[0.2em] px-8 py-4 rounded-xl transition-all flex items-center justify-center gap-3 uppercase italic shadow-lg shadow-accent/20"
                                            >
                                                Refine Strategy <RefreshCw size={14} className={refinementFeedback.trim() ? "animate-spin-slow" : ""} />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </motion.section>
                        )}
                    </AnimatePresence>
                </div>
            </main >
        </div >
    );
};

const MockupCard = ({ title, icon, desc, onClick }) => (
    <button onClick={onClick} className="glass-card p-8 rounded-3xl text-left hover:border-primary/50 transition-all group overflow-hidden relative">
        <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-primary/5 rounded-full group-hover:bg-primary/10 transition-colors" />
        <div className="bg-primary/10 p-4 rounded-2xl w-fit mb-6 text-primary group-hover:scale-110 transition-transform">{React.cloneElement(icon, { size: 28 })}</div>
        <h3 className="text-xl font-bold text-white mb-3 tracking-tight group-hover:text-primary transition-colors">{title}</h3>
        <p className="text-sm text-slate-500 leading-relaxed max-w-[240px]">{desc}</p>
        <div className="mt-6 flex items-center gap-2 text-[10px] font-black text-primary uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity italic">Neural Briefing <ChevronRight size={12} /></div>
    </button>
);

const MetricMiniCard = ({ icon, label, value, color }) => (
    <div className="glass-card p-4 rounded-2xl border-white/5 bg-[#080a0f]/80 backdrop-blur-md flex items-center gap-4 border-l-2 border-l-primary/30">
        <div className={`p-2 rounded-lg bg-white/5 ${color}`}>{icon}</div>
        <div>
            <span className="text-[8px] font-black text-slate-600 uppercase tracking-widest block mb-1">{label}</span>
            <span className="text-xs font-black text-white font-mono uppercase italic">{value}</span>
        </div>
    </div>
);

const ResultCard = ({ title, content, onClick, version, isModified, hasHistory }) => {
    if (!content) return null;
    return (
        <button
            onClick={() => onClick({ title, content })}
            className={`glass-card p-10 rounded-[32px] border-white/5 bg-[#0d1117]/60 group hover:border-primary/30 transition-all text-left cursor-pointer w-full relative overflow-hidden ${hasHistory && isModified ? 'ring-1 ring-primary/20' : ''}`}
        >
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                    <h4 className="font-black text-xs uppercase tracking-[0.4em] text-primary italic">{title}</h4>
                    <div className="bg-white/5 px-2 py-0.5 rounded text-[8px] font-black text-slate-500 uppercase tracking-widest border border-white/5">v{version}</div>
                </div>
                {hasHistory && (
                    isModified ? (
                        <span className="bg-primary text-white text-[8px] font-black px-2 py-1 rounded tracking-[0.2em] shadow-lg shadow-primary/20 animate-pulse">MODIFIED</span>
                    ) : (
                        <span className="bg-white/5 text-slate-500 text-[8px] font-black px-2 py-1 rounded tracking-[0.2em] border border-white/5 uppercase">Stable</span>
                    )
                )}
                <div className="bg-primary/10 p-2 rounded-lg text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight size={14} />
                </div>
            </div>
            <div className="space-y-6">
                {Object.entries(content).slice(0, 3).map(([key, val], i) => (
                    <div key={i} className="space-y-2">
                        <span className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-600 block">{key.replace('_', ' ')}</span>
                        <p className="text-xs text-slate-400 leading-relaxed font-medium line-clamp-4 italic">
                            {Array.isArray(val) ? val.join(', ') : (typeof val === 'object' ? JSON.stringify(val) : val)}
                        </p>
                    </div>
                ))}
            </div>
            <div className="mt-8 pt-6 border-t border-white/5 text-[9px] font-black text-slate-600 uppercase tracking-widest group-hover:text-primary transition-colors italic">
                View Full Briefing
            </div>
        </button>
    );
};

const PitchSection = ({ title, content, highlight }) => {
    if (!content) return null;
    return (
        <div className="space-y-3 md:space-y-4 text-left">
            <h5 className="text-[8px] md:text-[9px] font-black uppercase tracking-[0.4em] text-slate-500 italic text-left">{title}</h5>
            <p className={`${highlight ? 'text-xl md:text-2xl text-primary font-black italic tracking-tighter uppercase leading-tight' : 'text-sm md:text-base text-slate-300 font-bold leading-snug tracking-tight'} text-left`}>
                {content}
            </p>
        </div>
    );
};

export default App;
