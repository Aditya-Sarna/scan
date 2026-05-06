import React from "react";

export const Header = () => {
    return (
        <header
            data-testid="site-header"
            className="sticky top-0 z-40 bg-white/85 backdrop-blur-md border-b hairline"
        >
            <div className="max-w-[1440px] mx-auto px-6 md:px-10 lg:px-14 py-4 flex items-center justify-between">
                <a
                    href="/"
                    data-testid="logo-link"
                    className="flex items-center gap-3 group"
                >
                    <div className="w-7 h-7 border border-black flex items-center justify-center">
                        <div className="w-2 h-2 bg-black group-hover:bg-alert transition-colors" />
                    </div>
                    <div className="flex flex-col leading-none">
                    <span className="font-display font-black text-[15px] tracking-tighter">
                        NEURO·CNN
                    </span>
                    <span className="text-[9px] uppercase tracking-[0.3em] text-black/60 mt-0.5">
                        Multi-cancer Image Analysis / v1.1
                    </span>
                    </div>
                </a>
                <nav className="hidden md:flex items-center gap-8 text-[11px] uppercase tracking-[0.2em] font-mono">
                    <a href="#datasets" data-testid="nav-datasets" className="hover:text-alert transition-colors">
                        Datasets
                    </a>
                    <a href="#analyzer" data-testid="nav-analyzer" className="hover:text-alert transition-colors">
                        Analyzer
                    </a>
                    <a href="#gallery" data-testid="nav-gallery" className="hover:text-alert transition-colors">
                        Samples
                    </a>
                    <a href="#how" data-testid="nav-how" className="hover:text-alert transition-colors">
                        How it works
                    </a>
                    <a href="#disclaimer" data-testid="nav-disclaimer" className="hover:text-alert transition-colors">
                        Disclaimer
                    </a>
                </nav>
                <div className="hidden md:flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-ok animate-pulse" />
                    <span className="text-[10px] uppercase tracking-[0.3em] font-mono text-black/70">
                        CNN · MobileNetV3 + Claude 4.5
                    </span>
                </div>
            </div>
        </header>
    );
};

export default Header;
