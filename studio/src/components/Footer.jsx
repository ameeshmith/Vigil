import React from 'react';
import { ArrowUp } from 'lucide-react';

export default function Footer() {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <footer className="relative py-12 md:py-16 border-t border-[#121212]/10 bg-[#ECE8DE]/60 text-[#121212]">
      <div className="max-w-[1720px] mx-auto px-6 md:px-12">
        
        {/* Top Watermark & Scroll To Top */}
        <div className="flex items-center justify-between pb-8 mb-8 border-b border-[#121212]/10">
          <span className="font-display font-extrabold text-4xl sm:text-6xl text-[#121212]">
            VIGIL<span className="text-[#FF3E14]">.</span>
          </span>

          <button
            onClick={scrollToTop}
            className="flex items-center gap-2 p-3 rounded-full border border-[#121212]/20 hover:bg-[#121212] hover:text-white transition-colors cursor-pointer text-xs font-mono-code"
          >
            <span>BACK TO TOP</span>
            <ArrowUp className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Clean Footer Info Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 font-mono-code text-xs text-[#6E6C65]">
          <div>
            <div className="text-[#121212] font-bold uppercase mb-1">PROJECT</div>
            <p className="leading-relaxed">
              Vigil AI is an open research demo exploring agentic workflows in pharmacovigilance using LangGraph, FastMCP, and Groq.
            </p>
          </div>

          <div>
            <div className="text-[#121212] font-bold uppercase mb-1">DATA SOURCES</div>
            <p className="leading-relaxed">
              Powered entirely by public data: openFDA FAERS adverse events, openFDA drug label endpoints, and NCBI PubMed E-utilities.
            </p>
          </div>

          <div>
            <div className="text-[#121212] font-bold uppercase mb-1">DISCLAIMER</div>
            <p className="leading-relaxed text-[#121212]/80">
              Educational demo only. Spontaneous reporting data is subject to reporting biases and does not establish medical causation. Not clinical advice.
            </p>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-[#121212]/10 flex flex-col sm:flex-row items-center justify-between gap-4 font-mono-code text-[11px] text-[#6E6C65]">
          <div>&copy; 2026 Vigil AI &middot; Open Research Prototype</div>
          <div>Zero LLM Math &middot; Evans Criteria Compliant</div>
        </div>

      </div>
    </footer>
  );
}
