import React from "react";
import { ArrowDownRight } from "lucide-react";

export const Hero = () => {
    return (
        <section
            data-testid="hero-section"
            className="relative border-b hairline overflow-hidden"
        >
            <div className="max-w-[1440px] mx-auto px-6 md:px-10 lg:px-14 pt-16 md:pt-24 pb-14 md:pb-20">
                <div className="grid grid-cols-12 gap-6 md:gap-10">
                    <div className="col-span-12 lg:col-span-2">
                        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.3em] font-mono">
                            <span className="w-1.5 h-1.5 bg-alert" />
                            <span>01 / Index</span>
                        </div>
                    </div>

                    <div className="col-span-12 lg:col-span-7">
                        <h1
                            data-testid="hero-title"
                            className="font-display font-black text-[clamp(46px,8vw,124px)] leading-[0.86] tracking-[-0.05em]"
                        >
                            Multi-cancer
                            <br />
                            image analysis,
                            <br />
                            <span className="italic font-light">
                                read like a&nbsp;
                            </span>
                            <span className="relative inline-block">
                                doctor.
                                <span className="absolute -bottom-1 left-0 right-0 h-[6px] bg-alert -z-0" />
                            </span>
                        </h1>
                    </div>

                    <div className="col-span-12 lg:col-span-3 flex flex-col justify-end gap-6">
                        <p className="text-sm leading-relaxed font-mono text-black/70 max-w-sm">
                            Five pipelines across the body — brain, lung,
                            breast, skin, kidney. A real CNN classifies the
                            image, Claude drafts the report. Drop a scan or
                            try a sample.
                        </p>
                        <a
                            href="#analyzer"
                            data-testid="hero-cta"
                            className="inline-flex items-center gap-2 self-start border-2 border-black bg-black text-white px-5 py-3 font-mono text-xs uppercase tracking-[0.18em] hover:bg-white hover:text-black transition-colors"
                        >
                            Start analysis
                            <ArrowDownRight className="w-4 h-4" />
                        </a>
                    </div>
                </div>

                <div className="mt-14 md:mt-20 grid grid-cols-2 md:grid-cols-4 border-t border-black/10 divide-x divide-black/10">
                    {[
                        ["Pipelines", "05"],
                        ["Body parts", "Brain · Lung · Breast · Skin · Kidney"],
                        ["Classifier", "Trained CNN"],
                        ["Reasoning", "Claude 4.5"],
                    ].map(([k, v]) => (
                        <div key={k} className="px-4 md:px-6 py-5">
                            <div className="text-[10px] uppercase tracking-[0.28em] text-black/50 font-mono">
                                {k}
                            </div>
                            <div className="font-display font-bold text-2xl md:text-3xl tracking-tight mt-1">
                                {v}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Marquee strip */}
            <div className="border-t border-black overflow-hidden bg-black text-white">
                <div className="ticker-track py-3 text-[11px] uppercase tracking-[0.4em] font-mono">
                    {Array.from({ length: 2 }).flatMap((_, i) => [
                        "Brain MRI",
                        "Lung CT",
                        "Breast Ultrasound",
                        "Skin Dermoscopy",
                        "Kidney CT",
                        "MobileNetV3-Small",
                        "Cosine prototype head",
                        "Claude 4.5 report",
                        "Not a medical device",
                    ].map((t, j) => (
                        <span key={`${i}-${j}`} className="px-8 whitespace-nowrap inline-flex items-center gap-8">
                            {t}
                            <span className="w-1 h-1 bg-alert rounded-full" />
                        </span>
                    )))}
                </div>
            </div>
        </section>
    );
};

export default Hero;
Hero;
