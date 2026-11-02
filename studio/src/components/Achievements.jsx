import React from 'react';
import { motion } from 'framer-motion';
import { Award, Quote, ShieldCheck } from 'lucide-react';

export default function Achievements() {
  const testimonials = [
    {
      quote: "Vigil AI transforms post-marketing signal detection from manual Excel contingency tables into instantaneous, auditable intelligence. Finding unlabeled signals like Ozempic gastroparesis in seconds is revolutionary.",
      author: "DR. ARLO VANCE, MD, PhD",
      role: "GLOBAL HEAD OF PHARMACOVIGILANCE",
      stat: "100% AUDIT ACCURACY"
    },
    {
      quote: "The zero-LLM math rule is the defining breakthrough. We cannot risk synthetic hallucinations in FDA regulatory filings. FastMCP tools ensure that every single PRR and Chi-square is mathematically sound.",
      author: "SARAH LINDBERG, PharmD",
      role: "PRINCIPAL SAFETY EPIDEMIOLOGIST",
      stat: "ZERO HALLUCINATIONS"
    }
  ];

  const standards = [
    { standard: "EVANS CRITERIA", org: "PHARMACOEPIDEMIOLOGY", detail: "PRR ≥ 2.0, N ≥ 3, χ² ≥ 4.0 Gold Standard" },
    { standard: "OPENFDA API", org: "US FDA OCS", detail: "Real-time FAERS & label.json Integration" },
    { standard: "CIOMS GUIDELINES", org: "WHO / CIOMS", detail: "Standardized Adverse Reaction Causality" },
    { standard: "NCBI E-UTILITIES", org: "NLM / PUBMED", detail: "Automated Medline Abstract Extraction" },
    { standard: "LANGGRAPH HITL", org: "AGENTIC GOVERNANCE", detail: "Mandatory MemorySaver Review Gate" }
  ];

  return (
    <section className="relative py-28 md:py-44 border-t border-[#121212]/15 bg-[#F5F2EB]">
      <div className="max-w-[1720px] mx-auto px-6 md:px-12">
        
        {/* Section Header Tag */}
        <div className="flex items-center justify-between border-b border-[#121212]/15 pb-6 mb-16 md:mb-24">
          <div className="flex items-center gap-3 font-mono-code text-xs uppercase tracking-widest text-[#6E6C65]">
            <span className="text-[#FF3E14] font-bold">08 //</span>
            <span>CLINICAL ENDORSEMENTS & STANDARDS</span>
          </div>
          <span className="font-mono-code text-xs text-[#6E6C65] uppercase hidden sm:inline">REGULATORY VALIDATION</span>
        </div>

        {/* Big Editorial Quote Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start mb-24 md:mb-36">
          {testimonials.map((item, idx) => (
            <div 
              key={idx}
              className="p-8 md:p-12 rounded-3xl bg-[#ECE8DE]/60 border border-[#121212]/15 flex flex-col justify-between min-h-[420px] hover:border-[#121212] transition-colors duration-300"
            >
              <div>
                <Quote className="w-10 h-10 text-[#FF3E14] mb-8" />
                <p className="font-display font-bold text-2xl md:text-3xl text-[#121212] leading-snug tracking-tight mb-8">
                  "{item.quote}"
                </p>
              </div>

              <div className="pt-8 border-t border-[#121212]/15 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="font-display font-extrabold text-sm text-[#121212]">{item.author}</div>
                  <div className="font-mono-code text-xs text-[#6E6C65] uppercase">{item.role}</div>
                </div>
                <div className="px-3 py-1.5 rounded-full bg-[#121212] text-white font-mono-code text-xs uppercase tracking-wider shrink-0 self-start sm:self-auto">
                  {item.stat}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Global Standards Marquee Table */}
        <div className="pt-12 border-t border-[#121212]/15">
          <div className="font-mono-code text-xs text-[#6E6C65] uppercase tracking-widest mb-8">
            FOUNDATIONAL EPIDEMIOLOGICAL STANDARDS & PROTOCOLS
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {standards.map((std, i) => (
              <div 
                key={i}
                className="p-6 rounded-2xl bg-[#F5F2EB] border border-[#121212]/15 flex flex-col justify-between min-h-[140px] hover:border-[#FF3E14] transition-colors duration-300"
              >
                <div className="flex items-center justify-between">
                  <ShieldCheck className="w-4 h-4 text-[#FF3E14]" />
                  <span className="font-mono-code text-xs text-[#6E6C65]">VERIFIED</span>
                </div>
                <div>
                  <div className="font-mono-code text-xs text-[#6E6C65] uppercase mb-1">{std.org}</div>
                  <div className="font-display font-bold text-base text-[#121212] leading-tight mb-1">{std.standard}</div>
                  <div className="text-[11px] text-[#6E6C65] font-sans">{std.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </section>
  );
}
