import React from "react";
import { ArrowUpRight } from "lucide-react";

export const SampleGallery = ({ samples, onPick, busy }) => {
    return (
        <section
            id="gallery"
            data-testid="gallery-section"
            className="border-b hairline"
        >
            <div className="max-w-[1440px] mx-auto px-6 md:px-10 lg:px-14 py-14 md:py-20">
                <div className="grid grid-cols-12 gap-6 md:gap-10 mb-10">
                    <div className="col-span-12 lg:col-span-3">
                        <div className="text-[10px] uppercase tracking-[0.3em] font-mono text-black/50 mb-3">
                            03 / Reference set
                        </div>
                        <h2 className="font-display font-bold text-3xl md:text-4xl tracking-tight leading-[1]">
                            Or pick a&nbsp;sample.
                        </h2>
                    </div>
                    <div className="col-span-12 lg:col-span-7 lg:col-start-6">
                        <p className="text-sm font-mono text-black/70 leading-relaxed">
                            Four reference scans — one per class — drawn from
                            open MRI archives. Click to push it through the
                            pipeline and see a draft report appear below.
                        </p>
                    </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-0 border border-black/10">
                    {samples?.map((s, idx) => (
                        <button
                            key={s.id}
                            type="button"
                            onClick={() => !busy && onPick(s)}
                            data-testid={`sample-${s.category}`}
                            disabled={busy}
                            className={`group relative text-left bg-white border-black/10 ${
                                idx > 0 ? "lg:border-l sm:border-l" : ""
                            } ${idx >= 2 ? "border-t lg:border-t-0" : ""} ${
                                idx === 1 ? "border-t sm:border-t-0" : ""
                            } hover:bg-paper-3 transition-colors disabled:opacity-50`}
                        >
                            <div className="aspect-square bg-black overflow-hidden">
                                <img
                                    src={s.url}
                                    alt={s.label}
                                    className="w-full h-full object-cover grayscale group-hover:grayscale-0 group-hover:scale-105 transition-all duration-500 ease-out"
                                    crossOrigin="anonymous"
                                />
                            </div>
                            <div className="p-5 flex items-start justify-between gap-3">
                                <div>
                                    <div className="text-[10px] uppercase tracking-[0.28em] font-mono text-black/50">
                                        Class {String(idx + 1).padStart(2, "0")}
                                    </div>
                                    <div className="font-display font-bold text-xl tracking-tight mt-1">
                                        {s.label}
                                    </div>
                                    <div className="text-[11px] font-mono text-black/60 mt-1.5 leading-snug">
                                        {s.description}
                                    </div>
                                </div>
                                <ArrowUpRight className="w-5 h-5 mt-1 -translate-y-0 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                            </div>
                        </button>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default SampleGallery;
