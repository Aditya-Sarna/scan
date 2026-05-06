import React, { useCallback, useRef, useState } from "react";
import { Upload, ImagePlus, X } from "lucide-react";
import { toast } from "sonner";

const ACCEPTED = ["image/jpeg", "image/jpg", "image/png", "image/webp"];

const fileToBase64 = (file) =>
    new Promise((resolve, reject) => {
        const fr = new FileReader();
        fr.onload = () => resolve(fr.result);
        fr.onerror = reject;
        fr.readAsDataURL(file);
    });

export const UploadZone = ({ onAnalyze, busy, preview, onClearPreview, dataset }) => {
    const [drag, setDrag] = useState(false);
    const [context, setContext] = useState("");
    const inputRef = useRef(null);

    const handleFile = useCallback(
        async (file) => {
            if (!file) return;
            if (!ACCEPTED.includes(file.type)) {
                toast.error(`Unsupported format: ${file.type || "unknown"}. Use JPG, PNG, or WEBP.`);
                return;
            }
            if (file.size > 10 * 1024 * 1024) {
                toast.error("File too large (max 10MB)");
                return;
            }
            const dataUrl = await fileToBase64(file);
            onAnalyze({
                dataUrl,
                mime: file.type,
                base64: dataUrl.split(",")[1],
                filename: file.name,
                context: context.trim() || null,
            });
        },
        [onAnalyze, context]
    );

    const onDrop = (e) => {
        e.preventDefault();
        setDrag(false);
        const f = e.dataTransfer.files?.[0];
        if (f) handleFile(f);
    };

    return (
        <section
            id="analyzer"
            data-testid="analyzer-section"
            className="border-b hairline"
        >
            <div className="max-w-[1440px] mx-auto px-6 md:px-10 lg:px-14 py-14 md:py-20">
                <div className="grid grid-cols-12 gap-6 md:gap-10">
                    <div className="col-span-12 lg:col-span-3">
                        <div className="text-[10px] uppercase tracking-[0.3em] font-mono text-black/50 mb-3">
                            03 / Drop zone
                        </div>
                        <h2 className="font-display font-bold text-3xl md:text-4xl tracking-tight leading-[1]">
                            Drag &amp; drop the&nbsp;scan.
                        </h2>
                        {dataset && (
                            <div className="mt-4 inline-flex items-center gap-2 border border-black/15 bg-white px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.22em]">
                                <span className="w-1.5 h-1.5 bg-alert" />
                                Routing to · {dataset.name}
                            </div>
                        )}
                        <p className="mt-4 text-sm font-mono text-black/70 leading-relaxed">
                            JPG, PNG or WEBP up to 10MB. The pipeline first
                            verifies the image type matches the selected
                            dataset before the CNN runs.
                        </p>

                        <label className="block mt-6">
                            <span className="text-[10px] uppercase tracking-[0.28em] font-mono text-black/50">
                                Patient context (optional)
                            </span>
                            <textarea
                                data-testid="patient-context-input"
                                value={context}
                                onChange={(e) => setContext(e.target.value)}
                                placeholder="e.g. 42 y/o male, 3-week headache, blurred vision"
                                className="mt-2 w-full border border-black/15 bg-white p-3 font-mono text-xs h-24 focus:outline-none focus:border-black resize-none"
                            />
                        </label>
                    </div>

                    <div className="col-span-12 lg:col-span-9">
                        <div
                            data-testid="dropzone"
                            onDragOver={(e) => {
                                e.preventDefault();
                                setDrag(true);
                            }}
                            onDragLeave={() => setDrag(false)}
                            onDrop={onDrop}
                            onClick={() => !preview && inputRef.current?.click()}
                            className={`relative border-2 border-dashed transition-all min-h-[420px] flex flex-col items-center justify-center text-center cursor-pointer overflow-hidden ${
                                drag
                                    ? "border-alert bg-[#fff5f6]"
                                    : "border-black/25 bg-paper-3 hover:border-black/60"
                            } ${busy ? "pointer-events-none" : ""}`}
                        >
                            <input
                                ref={inputRef}
                                type="file"
                                accept="image/jpeg,image/png,image/webp"
                                className="hidden"
                                data-testid="file-input"
                                onChange={(e) => handleFile(e.target.files?.[0])}
                            />

                            {preview ? (
                                <div className="relative w-full h-full min-h-[420px]">
                                    <img
                                        src={preview}
                                        alt="Uploaded scan"
                                        data-testid="preview-image"
                                        className="w-full h-full object-contain max-h-[520px] mix-blend-multiply"
                                    />
                                    {busy && (
                                        <>
                                            <div className="absolute inset-0 bg-white/40" />
                                            <div className="scanline" />
                                            <div className="absolute bottom-4 left-4 right-4 flex items-center gap-3 bg-black text-white px-4 py-2.5 font-mono text-[11px] uppercase tracking-[0.25em]">
                                                <span className="w-2 h-2 bg-alert animate-pulse" />
                                                Reading scan…
                                            </div>
                                        </>
                                    )}
                                    {!busy && (
                                        <button
                                            type="button"
                                            data-testid="clear-preview-btn"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onClearPreview?.();
                                            }}
                                            className="absolute top-3 right-3 bg-white border border-black/20 hover:bg-black hover:text-white px-3 py-2 font-mono text-[10px] uppercase tracking-[0.25em] flex items-center gap-2"
                                        >
                                            <X className="w-3 h-3" />
                                            Clear
                                        </button>
                                    )}
                                </div>
                            ) : (
                                <div className="px-8 py-12">
                                    <div className="w-14 h-14 mx-auto border-2 border-black flex items-center justify-center mb-6">
                                        <Upload className="w-6 h-6" />
                                    </div>
                                    <div className="font-display font-bold text-2xl md:text-3xl tracking-tight">
                                        {drag ? "Release to analyze" : "Drop the MRI here"}
                                    </div>
                                    <p className="mt-3 font-mono text-xs text-black/60 uppercase tracking-[0.2em]">
                                        or click to browse — jpg · png · webp
                                    </p>

                                    <div className="mt-10 flex items-center justify-center gap-3 flex-wrap">
                                        <span
                                            type="button"
                                            data-testid="browse-btn"
                                            className="inline-flex items-center gap-2 border-2 border-black bg-black text-white px-5 py-3 font-mono text-xs uppercase tracking-[0.18em] hover:bg-white hover:text-black transition-colors"
                                        >
                                            <ImagePlus className="w-4 h-4" />
                                            Choose file
                                        </span>
                                        <a
                                            href="#gallery"
                                            data-testid="goto-gallery-link"
                                            onClick={(e) => e.stopPropagation()}
                                            className="inline-flex items-center gap-2 border-2 border-black/20 px-5 py-3 font-mono text-xs uppercase tracking-[0.18em] hover:border-black"
                                        >
                                            Or pick a sample
                                        </a>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Crosshair corners decor */}
                        <div className="grid grid-cols-3 gap-2 mt-3 text-[9px] uppercase tracking-[0.3em] font-mono text-black/50">
                            <span>// dropzone</span>
                            <span className="text-center">// 1024 × 1024</span>
                            <span className="text-right">// vision verified</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default UploadZone;
