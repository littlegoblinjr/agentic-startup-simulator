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
    Target
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
        if (activeRunId && (runStatus?.status === 'running' || runStatus?.status === 'pending')) {
            interval = setInterval(async () => {
                const status = await api.getStatus(activeRunId);
                setRunStatus(status);
                const logData = await api.getLogs(activeRunId);
                setLogs(logData.events || []);

                if (status.status === 'completed') {
                    clearInterval(interval);
                    setView('results');
                    loadRuns();
                }
            }, 2000);
        }
        return () => clearInterval(interval);
    }, [activeRunId, runStatus]);

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const loadRuns = async () => {
        const data = await api.listRuns();
        setRuns(data);
    };

    const startSimulation = async () => {
        if (!idea.trim()) return;
        setError(null);
        try {
            const runId = await api.simulate(idea);
            setActiveRunId(runId);
            setLogs([]);
            setRunStatus({ status: 'pending' });
            setView('monitor');
        } catch (err) {
            const msg = err.response?.data?.detail || "Simulation failed to start. Please check your prompt.";
            setError(msg);
            console.error("Simulation error:", err);
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
    const tokenMetrics = useMemo(() => {
        const totalTokens = logs.reduce((sum, log) => sum + (log.usage?.total_tokens || 0), 0);
        const avgTokensPerRequest = logs.length > 0 ? Math.round(totalTokens / logs.filter(l => l.usage).length) || 0 : 0;
        // Mock "Capability Density" calculation: tokens / uniqueness of thoughts (highly stylized)
        const density = totalTokens > 0 ? (logs.length * 100 / (totalTokens / 1000)).toFixed(1) : 0;
        return { totalTokens, avgTokensPerRequest, density };
    }, [logs]);

    return (
        <div className="flex h-screen bg-background font-sans text-slate-300 relative">
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
                            className="glass-card max-w-2xl w-full p-16 rounded-[48px] border-white/10 shadow-2xl relative bg-[#0d1117] text-left"
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
                            className="glass-card max-w-4xl w-full p-16 rounded-[48px] border-white/10 shadow-2xl relative bg-[#0b0e14] text-left max-h-[85vh] overflow-y-auto custom-scrollbar"
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
            {/* Sidebar */}
            <aside className="w-80 bg-[#05070a] border-r border-white/5 flex flex-col p-8 z-20">
                <div className="flex items-center gap-3 mb-12 px-2">
                    <Rocket className="text-primary w-8 h-8 rotate-45" />
                    <h1 className="text-xl font-black tracking-tighter text-white uppercase italic">Launchpad AI</h1>
                </div>

                <nav className="space-y-3 mb-12">
                    <button
                        onClick={() => setView('dashboard')}
                        className={`w-full flex items-center gap-4 px-5 py-3.5 rounded-2xl transition-all ${view === 'dashboard' ? 'bg-primary/10 text-primary border border-primary/20' : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'}`}
                    >
                        <LayoutDashboard size={20} />
                        <span className="font-bold uppercase text-xs tracking-widest">Console</span>
                    </button>

                    {activeRunId && (
                        <button
                            onClick={() => setView(runStatus?.status === 'completed' ? 'results' : 'monitor')}
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
                        {runs.map(run => (
                            <button
                                key={run.run_id}
                                onClick={() => selectRun(run.run_id)}
                                className={`w-full text-left p-5 rounded-2xl glass-card transition-all group relative border-white/5 ${activeRunId === run.run_id ? 'border-primary/40 bg-primary/5' : 'hover:border-primary/40'}`}
                            >
                                <p className="text-xs font-bold text-slate-300 line-clamp-2 mb-3 leading-relaxed">{run.idea}</p>
                                <div className="flex items-center justify-between">
                                    <span className="text-[9px] font-mono text-slate-600 uppercase">{new Date(run.created_at).toLocaleDateString()}</span>
                                    {run.score && (
                                        <span className="text-[9px] font-black text-primary border border-primary/30 px-2 py-0.5 rounded-full bg-primary/5 uppercase">
                                            {run.score} PTs
                                        </span>
                                    )}
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-y-auto relative z-10">
                <div className="max-w-6xl mx-auto px-16 py-16">
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
                                    <h2 className="text-6xl font-black text-white leading-none tracking-tighter uppercase italic">
                                        Simulate Your <br />
                                        <span className="text-primary italic">Startup Success.</span>
                                    </h2>
                                    <p className="text-slate-500 text-lg font-medium tracking-tight">
                                        Validate, test, and grow your startup ideas with <br />advanced AI simulations.
                                    </p>
                                </header>

                                <div className="w-full max-w-4xl relative group">
                                    <div className="absolute -inset-1 bg-gradient-to-r from-primary to-accent rounded-[32px] blur opacity-25 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
                                    <div className={`relative flex items-center bg-[#0d1117] border ${error ? 'border-red-500/50' : 'border-white/10'} rounded-[28px] p-2 pr-2 shadow-2xl search-glow`}>
                                        <div className="pl-8 text-slate-500">
                                            <Search size={24} />
                                        </div>
                                        <input
                                            type="text"
                                            value={idea}
                                            onChange={(e) => {
                                                setIdea(e.target.value);
                                                if (error) setError(null);
                                            }}
                                            maxLength={1000}
                                            placeholder="Enter your startup idea (e.g. AI-driven supply chain optimization)..."
                                            className="flex-1 bg-transparent border-none py-6 px-4 text-white text-lg focus:outline-none placeholder:text-slate-600"
                                        />
                                        <button
                                            onClick={startSimulation}
                                            className="bg-primary hover:bg-primary/90 text-white font-black text-xs tracking-[0.2em] px-8 py-5 rounded-[22px] transition-all flex items-center gap-3 uppercase italic shadow-lg shadow-primary/20"
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

                                <div className="grid grid-cols-2 gap-8 w-full max-w-4xl">
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
                                <div className="flex items-center justify-between border-b border-white/5 pb-8">
                                    <header>
                                        <div className="flex items-center gap-3 text-primary mb-3">
                                            <Zap size={18} fill="currentColor" />
                                            <span className="text-[10px] font-black uppercase tracking-[0.4em] italic">Telemetry Uplink Active</span>
                                        </div>
                                        <h2 className="text-4xl font-black text-white uppercase italic tracking-tighter">Processing Neural Loop...</h2>
                                    </header>

                                    {/* Real-time Token Metrics Badge */}
                                    <div className="flex items-center gap-4">
                                        <div className="glass-card px-6 py-3 rounded-2xl border-white/5 flex items-center gap-8">
                                            <div className="text-center">
                                                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block mb-1">Metabolism</span>
                                                <span className="text-sm font-black text-primary font-mono">{tokenMetrics.totalTokens}<span className="text-[9px] ml-1">TK</span></span>
                                            </div>
                                            <div className="text-center border-l border-white/10 pl-8">
                                                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest block mb-1">Density</span>
                                                <span className="text-sm font-black text-accent font-mono">{tokenMetrics.density}</span>
                                            </div>
                                        </div>
                                        <div className="bg-primary/5 px-8 py-4 rounded-3xl border border-primary/20 flex items-center gap-4">
                                            <motion.div animate={{ scale: [1, 1.4, 1], opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.5, repeat: Infinity }} className="w-2.5 h-2.5 bg-primary rounded-full shadow-[0_0_10px_rgba(79,70,229,0.8)]" />
                                            <span className="text-xs font-black font-mono text-primary tracking-widest uppercase italic">{runStatus?.status}</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="glass-card rounded-[32px] overflow-hidden flex flex-col h-[700px] border-white/5 shadow-neon-glow relative bg-[#020305]">
                                    {/* Sidebar for metrics inside terminal */}
                                    <div className="absolute top-20 right-8 w-64 space-y-4 z-20">
                                        <MetricMiniCard icon={<Coins size={14} />} label="Avg Tokens / Request" value={tokenMetrics.avgTokensPerRequest} color="text-indigo-400" />
                                        <MetricMiniCard icon={<Target size={14} />} label="Cost / Successful Task" value={`$${(tokenMetrics.totalTokens * 0.000005).toFixed(4)}`} color="text-emerald-400" />
                                    </div>

                                    <div className="bg-[#05070a] p-5 border-b border-white/5 flex items-center justify-between">
                                        <div className="flex items-center gap-6">
                                            <div className="flex gap-2">
                                                <div className="w-2.5 h-2.5 rounded-full bg-red-500/30"></div>
                                                <div className="w-2.5 h-2.5 rounded-full bg-amber-500/30"></div>
                                                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/30"></div>
                                            </div>
                                            <span className="text-[10px] font-bold font-mono text-slate-500 tracking-[0.2em] uppercase border-l border-white/10 pl-6">
                                                Simulator_Engine // RunID: {activeRunId?.substring(0, 8)}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex-1 overflow-y-auto p-10 space-y-6 agent-terminal custom-scrollbar">
                                        {logs.map((log, i) => (
                                            <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} key={i} className="text-xs border-l border-white/5 pl-6 py-2">
                                                <div className="flex items-center gap-4 mb-2">
                                                    <span className="text-[10px] text-slate-700 font-mono">[{log.timestamp.split('T')[1].split('.')[0]}]</span>
                                                    <span className={`px-2.5 py-1 rounded-md text-[9px] font-black uppercase tracking-widest ${log.agent_type.includes('market') ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' :
                                                        log.agent_type.includes('tech') ? 'bg-violet-500/10 text-violet-400 border border-violet-500/20' :
                                                            log.agent_type.includes('finance') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                                                'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                                        }`}>
                                                        {log.agent_type}
                                                    </span>
                                                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest italic">› {log.event_type}</span>
                                                    {log.usage && (
                                                        <span className="text-[9px] font-mono text-slate-700 ml-auto flex items-center gap-2">
                                                            <Coins size={10} /> {log.usage.total_tokens}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="text-slate-600 font-mono text-[11px] leading-relaxed max-w-2xl overflow-hidden whitespace-nowrap overflow-ellipsis">
                                                    {JSON.stringify(log.data, null, 2)}
                                                </div>
                                            </motion.div>
                                        ))}
                                        <div ref={logEndRef} />
                                    </div>
                                </div>
                            </motion.section>
                        )}

                        {view === 'results' && runStatus?.results && (
                            <motion.section
                                key="results"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="space-y-16 pb-24"
                            >
                                <header className="flex items-end justify-between border-b border-white/5 pb-16">
                                    <div className="space-y-6 text-left">
                                        <div className="inline-flex items-center gap-3 bg-primary/10 text-primary px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border border-primary/20">
                                            <ShieldCheck size={14} /> Analysis Certified
                                        </div>
                                        <h2 className="text-5xl font-black text-white italic tracking-tighter uppercase text-left">{runStatus.results.idea}</h2>
                                        <p className="text-slate-500 font-medium text-lg text-left">Detailed Venture Architecture & Strategic Roadmap.</p>
                                    </div>

                                    <div className="flex items-center gap-12">
                                        <div className="text-right border-r border-white/5 pr-12">
                                            <span className="text-slate-600 text-[10px] font-black uppercase tracking-[0.4em] block mb-4 italic">Resource Efficiency</span>
                                            <div className="text-3xl font-black text-accent italic tracking-tighter leading-none">
                                                {tokenMetrics.density}<span className="text-xs text-slate-700 ml-1">INDEX</span>
                                            </div>
                                        </div>
                                        {runStatus.results.final_context?.evaluation_scorecard && (
                                            <div className="text-right">
                                                <span className="text-slate-600 text-[10px] font-black uppercase tracking-[0.4em] block mb-4 italic">Evaluation Quotient</span>
                                                <div className="text-7xl font-black text-white italic tracking-tighter leading-none">
                                                    {runStatus.results.final_context.evaluation_scorecard.total_score}<span className="text-2xl text-slate-800 ml-2">/100</span>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </header>

                                <div className="grid grid-cols-3 gap-10">
                                    <ResultCard title="Market Fit" content={runStatus.results.final_context?.market_analysis} onClick={setSelectedCard} />
                                    <ResultCard title="Technical Design" content={runStatus.results.final_context?.tech_architecture} onClick={setSelectedCard} />
                                    <ResultCard title="Financial Model" content={runStatus.results.final_context?.financial_plan} onClick={setSelectedCard} />
                                </div>

                                <div className="glass-card rounded-[48px] p-16 relative overflow-hidden border-white/5 bg-[#0d1117] shadow-neon-indigo">
                                    <div className="absolute top-0 right-0 p-16 opacity-[0.03] scale-150 rotate-12"><Rocket size={200} /></div>
                                    <h3 className="text-4xl font-black text-white mb-16 uppercase italic tracking-tighter flex items-center gap-6">
                                        <span className="bg-primary p-3 rounded-2xl text-white shadow-neon-indigo"><Zap size={28} /></span>
                                        The Neural Pitch
                                    </h3>
                                    <div className="grid grid-cols-1 gap-12 max-w-4xl text-left">
                                        <PitchSection title="Startup Name" content={runStatus.results.final_context?.pitch?.startup_name} highlight />
                                        <div className="grid grid-cols-2 gap-16">
                                            <PitchSection title="The Problem" content={runStatus.results.final_context?.pitch?.problem} />
                                            <PitchSection title="The Solution" content={runStatus.results.final_context?.pitch?.solution} />
                                        </div>
                                        <div className="grid grid-cols-2 gap-16 py-12 border-y border-white/5">
                                            <PitchSection title="Business Model" content={runStatus.results.final_context?.pitch?.business_model} />
                                            <PitchSection title="Advanced Tech" content={runStatus.results.final_context?.pitch?.technology} />
                                        </div>
                                        <PitchSection title="Global Vision" content={runStatus.results.final_context?.pitch?.vision} />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-8 text-left">
                                    <div className="glass-card p-10 rounded-[40px] space-y-8 bg-[#0d1117]/80 border-white/5">
                                        <h4 className="font-black text-xs uppercase tracking-[0.4em] text-primary italic">Critique Intelligence</h4>
                                        <div className="grid grid-cols-2 gap-8">
                                            <div>
                                                <span className="text-[10px] font-black text-emerald-500 uppercase tracking-widest block mb-4 italic">High Quality Indicators</span>
                                                <ul className="space-y-3">
                                                    {runStatus.results.final_context?.evaluation_scorecard?.feedback?.strengths?.map((s, i) => (
                                                        <li key={i} className="text-[11px] text-slate-400 flex items-start gap-3 leading-relaxed">
                                                            <span className="mt-1.5 w-1 h-1 rounded-full bg-emerald-500 shrink-0" /> {s}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                            <div>
                                                <span className="text-[10px] font-black text-rose-500 uppercase tracking-widest block mb-4 italic">Optimisation Required</span>
                                                <ul className="space-y-3">
                                                    {runStatus.results.final_context?.evaluation_scorecard?.feedback?.weaknesses?.map((s, i) => (
                                                        <li key={i} className="text-[11px] text-slate-400 flex items-start gap-3 leading-relaxed">
                                                            <span className="mt-1.5 w-1 h-1 rounded-full bg-rose-500 shrink-0" /> {s}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="bg-primary/5 border border-primary/20 p-12 rounded-[40px] flex flex-col justify-center text-center relative overflow-hidden">
                                        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/20 blur-[60px] rounded-full" />
                                        <h4 className="text-[10px] font-black uppercase tracking-[0.5em] text-primary mb-10 italic text-center">Executive Verdict</h4>
                                        <p className="text-3xl font-black italic text-white leading-tight tracking-tight uppercase text-center">
                                            "{runStatus.results.final_context?.evaluation_scorecard?.feedback?.investor_verdict}"
                                        </p>
                                    </div>
                                </div>
                            </motion.section>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
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

const ResultCard = ({ title, content, onClick }) => {
    if (!content) return null;
    return (
        <button
            onClick={() => onClick({ title, content })}
            className="glass-card p-10 rounded-[32px] border-white/5 bg-[#0d1117]/60 group hover:border-primary/30 transition-all text-left cursor-pointer w-full"
        >
            <div className="flex items-center justify-between mb-8">
                <h4 className="font-black text-xs uppercase tracking-[0.4em] text-primary italic">{title}</h4>
                <div className="bg-primary/10 p-2 rounded-lg text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight size={14} />
                </div>
            </div>
            <div className="space-y-6">
                {Object.entries(content).slice(0, 3).map(([key, val], i) => (
                    <div key={i} className="space-y-2">
                        <span className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-600 block">{key.replace('_', ' ')}</span>
                        <p className="text-xs text-slate-400 leading-relaxed font-medium line-clamp-4 italic">{Array.isArray(val) ? val.join(', ') : val}</p>
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
        <div className="space-y-4 text-left">
            <h5 className="text-[10px] font-black uppercase tracking-[0.5em] text-slate-500 italic text-left">{title}</h5>
            <p className={`${highlight ? 'text-5xl text-primary font-black italic tracking-tighter uppercase' : 'text-xl text-slate-300 font-bold leading-snug tracking-tight'} text-left`}>
                {content}
            </p>
        </div>
    );
};

export default App;
