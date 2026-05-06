import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Analyzer from "./pages/Analyzer";

function App() {
    return (
        <div className="App">
            <Toaster
                position="bottom-right"
                toastOptions={{
                    style: {
                        background: "#000",
                        color: "#fff",
                        border: "1px solid #000",
                        borderRadius: 0,
                        fontFamily: "'Geist Mono', monospace",
                        fontSize: "12px",
                        letterSpacing: "0.04em",
                    },
                }}
            />
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<Analyzer />} />
                </Routes>
            </BrowserRouter>
        </div>
    );
}

export default App;
