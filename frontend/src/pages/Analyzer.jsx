import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import Header from "../components/site/Header";
import Hero from "../components/site/Hero";
import UploadZone from "../components/site/UploadZone";
import SampleGallery from "../components/site/SampleGallery";
import AnalysisReport from "../components/site/AnalysisReport";
import HowItWorks from "../components/site/HowItWorks";
import Footer from "../components/site/Footer";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND}/api`;

// Convert any cross-origin image URL → base64 via canvas (avoids CORS reads)
async function urlToBase64(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
            try {
                const canvas = document.createElement("canvas");
                const max = 1024;
                let w = img.naturalWidth;
                let h = img.naturalHeight;
                if (w > max || h > max) {
                    const r = Math.min(max / w, max / h);
                    w = Math.round(w * r);
                    h = Math.round(h * r);
                }
                canvas.width = w;
                canvas.height = h;
                const ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0, w, h);
                const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
                resolve(dataUrl);
            } catch (e) {
                reject(e);
            }
        };
        img.onerror = () => reject(new Error("Failed to load sample image"));
        img.src = url;
    });
}

export default function Analyzer() {
    const [samples, setSamples] = useState([]);
    const [busy, setBusy] = useState(false);
    const [preview, setPreview] = useState(null); // dataURL
    const [result, setResult] = useState(null);
    const reportRef = useRef(null);

    useEffect(() => {
        axios
            .get(`${API}/sample-gallery`)
            .then((r) => setSamples(r.data?.samples || []))
            .catch(() => toast.error("Failed to load sample gallery"));
    }, []);

    const scrollToReport = () => {
        setTimeout(() => {
            document
                .getElementById("report")
                ?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 120);
    };

    const runAnalysis = async ({ dataUrl, base64, mime, context }) => {
        setBusy(true);
        setResult(null);
        setPreview(dataUrl);
        try {
            const r = await axios.post(`${API}/analyze`, {
                image_base64: base64,
                mime_type: mime || "image/jpeg",
                patient_context: context || null,
            }, { timeout: 60000 });
            setResult(r.data);
            if (r.data.is_mri) {
                toast.success(`Diagnosis drafted — ${r.data.classification_label}`);
            } else {
                toast.error("Image rejected — not a brain MRI");
            }
            scrollToReport();
        } catch (e) {
            console.error(e);
            const msg = e.response?.data?.detail || e.message || "Analysis failed";
            toast.error(typeof msg === "string" ? msg : "Analysis failed");
        } finally {
            setBusy(false);
        }
    };

    const pickSample = async (sample) => {
        setBusy(true);
        try {
            toast.message("Loading sample…", { duration: 1200 });
            const dataUrl = await urlToBase64(sample.url);
            await runAnalysis({
                dataUrl,
                base64: dataUrl.split(",")[1],
                mime: "image/jpeg",
                context: `Reference sample: ${sample.label}`,
            });
        } catch (e) {
            console.error(e);
            toast.error("Could not load that sample. Try uploading manually.");
            setBusy(false);
        }
    };

    const reset = () => {
        setResult(null);
        setPreview(null);
        document.getElementById("analyzer")?.scrollIntoView({ behavior: "smooth" });
    };

    return (
        <div className="min-h-screen bg-white text-black">
            <Header />
            <Hero />
            <UploadZone
                onAnalyze={runAnalysis}
                busy={busy}
                preview={preview}
                onClearPreview={() => {
                    setPreview(null);
                    setResult(null);
                }}
            />
            {result && (
                <div ref={reportRef}>
                    <AnalysisReport result={result} image={preview} onReset={reset} />
                </div>
            )}
            <SampleGallery samples={samples} onPick={pickSample} busy={busy} />
            <HowItWorks />
            <Footer />
        </div>
    );
}
