import React from "react";
import { Brain, Wind, Heart, Sparkles, CircleDot } from "lucide-react";

const ICONS = {
    brain_mri: Brain,
    lung_ct: Wind,
    breast_us: Heart,
    skin_derm: Sparkles,
    kidney_ct: CircleDot,
};

export const DatasetSelector = ({ datasets, selected, onSelect }) => {
    return (
        <section
            id="datasets"
            data-testid="datasets-section"
            className="border-b hairline"
        >
            <div className="max-w-[1440px] mx-auto px-6 md:px-10 lg:px-14 py-12 md:py-16">
                <div className="grid grid-cols-12 gap-6 md:gap-10 mb-8">
                    <div className="col-span-12 lg:col-span-3">
                        <div className="text-[10px] uppercase tracking-[0.3em] font-mono text-black/50 mb-3">
                            02 / Pipeline
                        </div>
                        <h2 className="font-display font-bold text-3xl md:text-4xl tracking-tight leading-[1]">
                            Pick a&nbsp;dataset.
                        </h2>
                    </div>
                    <div className="col-span-12 lg:col-span-7 lg:col-start-6">
                        <p className="text-sm font-mono text-black/70 leading-relaxed">
                            Each pipeline pairs a body-part-specific class set
                            with a CNN prototype head. Switch tabs to route
                            your image through a different model.
                        </p>
                    </div>
                </div>

                <div
                    data-testid="dataset-tabs"
                    className="grid grid-cols-2 md:grid-cols-5 gap-0 border border-black/15"
                >
                    {datasets?.map((d) => {
                        const Icon = ICONS[d.id] || Brain;
                        const active = selected?.id === d.id;
                        return (
                            <button
                                key={d.id}
                                type="button"
                                data-testid={`dataset-tab-${d.id}`}
                                aria-pressed={active}
                                onClick={() => onSelect(d)}
                                className={`relative text-left p-5 md:p-6 transition-colors border-black/10 group ${
                                    active
                                        ? "bg-black text-white"
                                        : "bg-white hover:bg-paper-3"
                                } [&:not(:first-child)]:border-l [&:nth-child(n+3)]:md:border-l [&:nth-child(n+3)]:max-md:border-t md:[&:nth-child(n+3)]:border-t-0`}
                            >
                                <div className="flex items-start justify-between">
                                    <Icon className="w-5 h-5" strokeWidth={1.5} />
                                    {active && (
                                        <span className="text-[9px] uppercase tracking-[0.3em] font-mono">
                                            Active
                                        </span>
                                    )}
                                </div>
                                <div className="mt-6 font-display font-bold text-xl md:text-2xl tracking-tight leading-[1.05]">
                                    {d.body_part}
                                </div>
                                <div className={`mt-1 text-[11px] font-mono uppercase tracking-[0.18em] ${active ? "text-white/70" : "text-black/55"}`}>
                                    {d.modality}
                                </div>
                                <div className={`mt-3 text-[11px] font-mono leading-snug ${active ? "text-white/80" : "text-black/65"}`}>
                                    {d.tagline}
                                </div>
                                <div className={`mt-4 text-[10px] font-mono uppercase tracking-[0.25em] ${active ? "text-white/60" : "text-black/40"}`}>
                                    {d.classes?.length || 0} classes
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>
        </section>
    );
};

export default DatasetSelector;
