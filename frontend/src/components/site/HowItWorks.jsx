import React from "react";

export const HowItWorks = () => {
    const steps = [
        {
            n: "01",
            t: "Validate",
            d: "A vision LLM checks every upload before anything else: is this actually a brain MRI? Photos, paper, X-rays — they get rejected with a reason.",
        },
        {
            n: "02",
            t: "Classify",
            d: "Once validated, the model assigns one of four labels — glioma, meningioma, pituitary, or no tumor — with a calibrated confidence score.",
        },
        {
            n: "03",
            t: "Reason",
            d: "Claude Sonnet 4.5 drafts a structured report: observations, key indicators, recommendations, and a triage urgency.",
        },
    ];
    return (
        <section
            id="how"
            data-testid="how-section"
            className="border-b hairline bg-paper-3"
        >
            <div className="max-w-[1440px] mx-auto px-6 md:px-10 lg:px-14 py-14 md:py-20">
                <div className="grid grid-cols-12 gap-6 md:gap-10 mb-10">
                    <div className="col-span-12 lg:col-span-3">
                        <div className="text-[10px] uppercase tracking-[0.3em] font-mono text-black/50 mb-3">
                            05 / Pipeline
                        </div>
                        <h2 className="font-display font-bold text-3xl md:text-4xl tracking-tight leading-[1]">
                            Three&nbsp;passes,
                            <br />
                            <span className="italic font-light">one verdict</span>.
                        </h2>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border border-black/15 bg-white">
                    {steps.map((s, i) => (
                        <div
                            key={s.n}
                            className={`p-7 md:p-9 ${i > 0 ? "md:border-l border-black/10" : ""} ${i > 0 ? "border-t md:border-t-0 border-black/10" : ""}`}
                        >
                            <div className="font-display font-black text-6xl md:text-7xl tracking-tighter">
                                {s.n}
                            </div>
                            <div className="mt-3 font-display font-bold text-2xl tracking-tight">
                                {s.t}
                            </div>
                            <p className="mt-3 font-mono text-xs leading-relaxed text-black/70 max-w-xs">
                                {s.d}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default HowItWorks;
