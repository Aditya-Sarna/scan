import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import Header from "../components/site/Header";
import Hero from "../components/site/Hero";
import DatasetSelector from "../components/site/DatasetSelector";
import UploadZone from "../components/site/UploadZone";
import SampleGallery from "../components/site/SampleGallery";
import AnalysisReport from "../components/site/AnalysisReport";
import HowItWorks from "../components/site/HowItWorks";
import Footer from "../components/site/Footer";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND}/api`;

export default function Analyzer() {
    const [datasets, setDatasets] = useState([]);
    const [selected, setSelected] = useState(null);
    const [busy, setBusy] = useState(false);
    const [preview, setPreview] = useState(null);
    const [result, setResult] = useState(null);
    const reportRef = useRef(null);

    useEffect(() => {
        axios
            .get(`${API}/datasets`)
            .then((r) => {
                const list = r.data?.datasets || [];
                setDatasets(list);
                if (list.length && !selected) setSelected(list[0]);
            })
            .catch(() => toast.error("Failed to load datasets"));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const scrollToReport = () => {
        setTimeout(() => {
            document.getElementById("report")?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 120);
    };

    const onSelectDataset = (d) => {
        setSelected(d);
        setResult(null);
        setPreview(null);
    };

    const runUploadAnalysis = async ({ dataUrl, base64, mime, context }) => {
        if (!selected) {
            toast.error("Pick a dataset first");
            return;
        }
        setBusy(true);
        setResult(null);
        setPreview(dataUrl);
        try {
            const r = await axios.post(
                `${API}/analyze`,
                {
                    image_base64: base64,
                    mime_type: mime || "image/jpeg",
                    dataset_id: selected.id,
                    patient_context: context || null,
                },
                { timeout: 90000 }
            );
            setResult(r.data);
            if (r.data.is_valid_image) {
                toast.success(`CNN: ${r.data.cnn?.predicted_label}`);
            } else {
                toast.error("Image rejected — wrong type for this pipeline");
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
        setResult(null);
        // Use proxied URL from backend → guaranteed to load (no CORS)
        const imgUrl = `${BACKEND}${sample.image_url}`;
        setPreview(imgUrl);
        try {
            toast.message("Running CNN…", { duration: 1200 });
            const r = await axios.post(
                `${API}/analyze-sample`,
                {
                    sample_id: sample.id,
                    patient_context: `Reference sample: ${sample.label}`,
                },
                { timeout: 90000 }
            );
            setResult(r.data);
            toast.success(`CNN: ${r.data.cnn?.predicted_label}`);
            scrollToReport();
        } catch (e) {
            console.error(e);
            const msg = e.response?.data?.detail || e.message || "Analysis failed";
            toast.error(typeof msg === "string" ? msg : "Analysis failed");
        } finally {
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
            <DatasetSelector
                datasets={datasets}
                selected={selected}
                onSelect={onSelectDataset}
            />
            <UploadZone
                dataset={selected}
                onAnalyze={runUploadAnalysis}
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
            <SampleGallery dataset={selected} onPick={pickSample} busy={busy} />
            <HowItWorks />
            <Footer />
        </div>
    );
}
