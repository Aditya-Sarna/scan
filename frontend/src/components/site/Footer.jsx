import React from "react";

export const Footer = () => {
    return (
        <footer
            id="disclaimer"
            data-testid="site-footer"
            className="bg-black text-white"
        >
            <div className="max-w-[1440px] mx-auto px-6 md:px-10 lg:px-14 py-14 md:py-20">
                <div className="grid grid-cols-12 gap-6 md:gap-10">
                    <div className="col-span-12 lg:col-span-7">
                        <div className="text-[10px] uppercase tracking-[0.3em] font-mono text-white/60">
                            07 / Disclaimer
                        </div>
                        <h3 className="font-display font-black text-4xl md:text-6xl tracking-tighter leading-[0.92] mt-4">
                            Not a medical&nbsp;device.
                            <br />
                            <span className="italic font-light text-white/70">
                                Always consult a&nbsp;clinician.
                            </span>
                        </h3>
                    </div>
                    <div className="col-span-12 lg:col-span-5 lg:pl-10 border-l border-white/10">
                        <p className="font-mono text-xs leading-relaxed text-white/75">
                            NEURO·MRI is an experimental research interface
                            built on top of large multimodal models. Outputs are
                            generated drafts intended for educational and
                            exploratory use only. They are not a diagnosis, not
                            a substitute for radiology review, and not approved
                            for clinical decision-making. If you suspect a
                            neurological issue, contact a licensed physician or
                            emergency services.
                        </p>
                        <div className="mt-8 grid grid-cols-2 gap-4 text-[10px] font-mono uppercase tracking-[0.25em] text-white/60">
                            <div>
                                <div className="text-white">Model</div>
                                <div className="mt-1">Claude Sonnet 4.5</div>
                            </div>
                            <div>
                                <div className="text-white">Build</div>
                                <div className="mt-1">v1.0 · Feb 2026</div>
                            </div>
                            <div>
                                <div className="text-white">License</div>
                                <div className="mt-1">Research preview</div>
                            </div>
                            <div>
                                <div className="text-white">Status</div>
                                <div className="mt-1 text-ok">● Live</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="mt-16 border-t border-white/15 pt-6 flex flex-wrap items-center justify-between gap-4 text-[10px] uppercase tracking-[0.3em] font-mono text-white/50">
                    <span>© 2026 NEURO·MRI Lab</span>
                    <span>Built for educational use</span>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
