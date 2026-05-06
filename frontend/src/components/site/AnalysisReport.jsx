import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Activity, FileText, Stethoscope, Cpu } from "lucide-react";

const URGENCY = {
    low: { label: "LOW", color: "text-ok", bg: "bg-ok/10", border: "border-ok/30" },
    moderate: { label: "MODERATE", color: "text-black", bg: "bg-black/5", border: "border-black/30" },
    high: { label: "HIGH", color: "text-alert", bg: "bg-alert/10", border: "border-alert/30" },
    critical: { label: "CRITICAL", color: "text-white", bg: "bg-alert", border: "border-alert" },
};

const Typewriter = ({ text, speed = 8 }) => {
    const [out, setOut] = useState("");
    useEffect(() => {
        if (!text) return;
        let i = 0;
        setOut("");
        const id = setInterval(() => {
            i++;
            setOut(text.slice(0, i));
            if (i >= text.length) clearInterval(id);
        }, speed);
        return () => clearInterval(id);
    }, [text, speed]);
    return <span className="cursor-blink">{out}</span>;
};

export const AnalysisReport = ({ result, image, onReset }) => {
    if (!result) return null;

    if (!result.is_valid_image) {
        return (
            <section
                id="report"
                data-testid="report-rejection"
                className="border-b hairline"
            >
                <div className="max-w-[1440px] mx-auto px-6 md:px-10 lg:px-14 py-14 md:py-20">
                    <div className="grid grid-cols-12 gap-6 md:gap-10">
                        <div className="col-span-12 lg:col-span-3">
                            <div className="text-[10px] uppercase tracking-[0.3em] font-mono text-alert mb-3">
                                05 / Rejected
                            </div>
                            <h2 className="font-display font-bold text-3xl md:text-4xl tracking-tight leading-[1]">
                                Wrong image for the&nbsp;
                                <span className="italic font-light">{result.body_part}</span>&nbsp;pipeline.
                            </h2>
                        </div>
                        <div className="col-span-12 lg:col-span-9">
                            <div className="border-2 border-alert bg-[#fff5f6] p-6 md:p-10">
                                <div className="flex items-start gap-4">
                                    <div className="w-10 h-10 border-2 border-alert flex items-center justify-center flex-shrink-0">
                                        <AlertTriangle className="w-5 h-5 text-alert" />
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-[10px] uppercase tracking-[0.3em] font-mono text-alert">
                                            Validation failed · {result.dataset_name}
                                        </div>
                                        <h3 className="font-display font-bold text-2xl mt-2 tracking-tight">
                                            We can&apos;t analyze this image.
                                        </h3>
                                        <p className="font-mono text-sm text-black/80 mt-3 leading-relaxed max-w-2xl">
                                            {result.rejection_reason ||
                                                "The uploaded file does not match the selected pipeline. Try a different image, or switch to a different dataset above."}
                                        </p>
                                        <button
                                            type="button"
                                            onClick={onReset}
                                            data-testid="reset-after-rejection-btn"
                                            className="mt-8 inline-flex items-center gap-2 border-2 border-black bg-black text-white px-5 py-3 font-mono text-xs uppercase tracking-[0.18em] hover:bg-white hover:text-black transition-colors"
                                        >
                                            Upload a different image
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        );
    }

    const cnn = result.cnn;
    const abnormal = !!result.abnormal_detected;
    const urgency = URGENCY[result.doctor_analysis?.urgency || "low"] || URGENCY.low;

    return (
        <section
            id="report"
            data-testid="report-section"
            className="border-b hairline animate-fade-up"
        >
            <div className="max-w-[1440px] mx-auto px-6 md:px-10 lg:px-14 py-14 md:py-20">
                <div className="grid grid-cols-12 gap-6 md:gap-10">
                    <div className="col-span-12 lg:col-span-3">
                        <div className="text-[10px] uppercase tracking-[0.3em] font-mono text-black/50 mb-3">
                            05 / Diagnostic draft
                        </div>
                        <h2 className="font-display font-bold text-3xl md:text-4xl tracking-tight leading-[1]">
                            Radiology&nbsp;<span className="italic font-light">report</span>.
                        </h2>
                        <div className="mt-6 inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-black/60 border border-black/10 px-3 py-1.5">
                            <FileText className="w-3 h-3" />
                            ID&nbsp;{result.id?.slice(0, 8)}
                        </div>
                        <div className="mt-3 inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-black/60 border border-black/10 px-3 py-1.5">
                            <Cpu className="w-3 h-3" />
                            {result.dataset_name}
                        </div>
                    </div>

                    <div className="col-span-12 lg:col-span-9">
                        <div className="grid grid-cols-1 md:grid-cols-2 border border-black/15">
                            {/* Image side */}
                            <div className="relative bg-black aspect-square md:aspect-auto md:min-h-[560px]">
                                {image && (
                                    <img
                                        src={image}
                                        alt="Analyzed scan"
                                        data-testid="report-image"
                                        className="w-full h-full object-contain"
                                    />
                                )}
                                <div className="absolute top-3 left-3 right-3 flex items-center justify-between text-[10px] font-mono uppercase tracking-[0.25em] text-white/80">
                                    <span>// {result.modality} · {result.body_part}</span>
                                    <span>{new Date(result.timestamp).toLocaleTimeString()}</span>
                                </div>
                                {/* Top-K bar */}
                                {cnn?.top_k?.length > 0 && (
                                    <div className="absolute bottom-3 left-3 right-3 bg-white/95 border border-black p-3" data-testid="topk-bar">
                                        <div className="text-[9px] uppercase tracking-[0.3em] font-mono text-black/55 mb-2">
                                            CNN · Top-{cnn.top_k.length}
                                        </div>
                                        <div className="space-y-1.5">
                                            {cnn.top_k.map((t) => (
                                                <div key={t.class_id} className="flex items-center gap-3">
                                                    <span className="font-mono text-[11px] w-40 truncate">{t.label}</span>
                                                    <div className="flex-1 h-1.5 bg-black/10 relative">
                                                        <div
                                                            className="absolute top-0 left-0 h-full bg-black"
                                                            style={{ width: `${Math.round(t.probability * 100)}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Report side */}
                            <div className="p-6 md:p-8 bg-white">
                                <div className="flex items-start justify-between gap-4 pb-5 border-b border-black/10">
                                    <div>
                                        <div className="text-[10px] uppercase tracking-[0.28em] font-mono text-black/50">
                                            CNN Diagnosis
                                        </div>
                                        <div className="font-display font-bold text-3xl md:text-4xl tracking-tight mt-1.5">
                                            {cnn?.predicted_label}
                                        </div>
                                        <div className="mt-3 flex flex-wrap items-center gap-2">
                                            <span
                                                data-testid="abnormal-badge"
                                                className={`inline-flex items-center gap-1.5 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.18em] border ${
                                                    abnormal
                                                        ? "bg-alert/10 text-alert border-alert/30"
                                                        : "bg-ok/10 text-ok border-ok/30"
                                                }`}
                                            >
                                                {abnormal ? <AlertTriangle className="w-3 h-3" /> : <CheckCircle2 className="w-3 h-3" />}
                                                {abnormal ? "Abnormal" : "Normal"}
                                            </span>
                                            <span
                                                className={`inline-flex items-center gap-1.5 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.18em] border ${urgency.bg} ${urgency.color} ${urgency.border}`}
                                            >
                                                <Activity className="w-3 h-3" />
                                                {urgency.label}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div className="py-3 text-[10px] font-mono uppercase tracking-[0.22em] text-black/40 border-b border-black/10">
                                    Model · {cnn?.model_arch}
                                </div>

                                {result.doctor_analysis && (
                                    <>
                                        <div className="py-5 border-b border-black/10">
                                            <div className="text-[10px] uppercase tracking-[0.28em] font-mono text-black/50 mb-2">
                                                Summary
                                            </div>
                                            <p data-testid="report-summary" className="font-display text-lg leading-snug tracking-tight">
                                                <Typewriter text={result.doctor_analysis.summary || ""} />
                                            </p>
                                        </div>
                                        <ReportList
                                            title="Observations"
                                            items={result.doctor_analysis.observations}
                                            testid="observations-list"
                                        />
                                        <ReportList
                                            title="Key indicators"
                                            items={result.doctor_analysis.key_indicators}
                                            testid="indicators-list"
                                        />
                                        <ReportList
                                            title="Recommendations"
                                            items={result.doctor_analysis.recommendations}
                                            icon={<Stethoscope className="w-3 h-3" />}
                                            testid="recommendations-list"
                                        />
                                        {result.doctor_analysis.differential_notes && (
                                            <div className="py-5 border-t border-black/10 mt-1">
                                                <div className="text-[10px] uppercase tracking-[0.28em] font-mono text-black/50 mb-2">
                                                    Differential notes
                                                </div>
                                                <p className="font-mono text-xs leading-relaxed text-black/80">
                                                    {result.doctor_analysis.differential_notes}
                                                </p>
                                            </div>
                                        )}
                                    </>
                                )}

                                <div className="pt-6 flex items-center justify-between gap-3">
                                    <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-black/50">
                                        AI draft — not a clinical decision
                                    </p>
                                    <button
                                        type="button"
                                        onClick={onReset}
                                        data-testid="run-another-btn"
                                        className="inline-flex items-center gap-2 border-2 border-black bg-white px-4 py-2 font-mono text-[11px] uppercase tracking-[0.2em] hover:bg-black hover:text-white transition-colors"
                                    >
                                        Run another
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};

const ReportList = ({ title, items, icon, testid }) => {
    if (!items?.length) return null;
    return (
        <div className="py-5 border-b border-black/10">
            <div className="text-[10px] uppercase tracking-[0.28em] font-mono text-black/50 mb-3 flex items-center gap-1.5">
                {icon}
                {title}
            </div>
            <ul data-testid={testid} className="space-y-2">
                {items.map((it, i) => (
                    <li key={i} className="flex items-start gap-3 font-mono text-xs leading-relaxed">
                        <span className="text-black/40 tnum mt-0.5">{String(i + 1).padStart(2, "0")}</span>
                        <span className="flex-1">{it}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default AnalysisReport;
