import React from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight } from 'lucide-react';

export default function Philosophy() {
  const principles = [
    {
      num: "I.",
      title: "ZERO PROBABILISTIC ARITHMETIC",
      desc: "Language models are inherently non-deterministic tokens predictors. Under no circumstance is the model permitted to do math. All 2×2 contingency ratios, PRRs, and confidence intervals are computed in deterministic Python tools."
    },
    {
      num: "II.",
      title: "MANDATORY HUMAN-IN-THE-LOOP GATE",
      desc: "Whenever an unlisted signal is detected or reporting volume is clinically sparse, LangGraph halts execution using MemorySaver interrupt(). The system never finalizes without clinical review."
    },
    {
      num: "III.",
      title: "TOTAL REGULATORY PROVENANCE",
      desc: "Every assertion must carry a verifiable citation—an exact openFDA FAERS query URL, an FDA package insert section, or a PubMed PMID. Mandatory pharmacovigilance limitations are permanently enforced."
    }
  ];

  return (
    <section id="philosophy" className="relative py-28 md:py-44 bg-[#0E0E10] text-[#F5F2EB] overflow-hidden">
      
      {/* Background radial accent glow */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-[#FF3E14]/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-[1720px] mx-auto px-6 md:px-12 relative z-10">
        
        {/* Section Header Tag */}
        <div className="flex items-center justify-between border-b border-white/15 pb-6 mb-16 md:mb-24">
          <div className="flex items-center gap-3 font-mono-code text-xs uppercase tracking-widest text-neutral-400">
            <span className="text-[#FF3E14] font-bold">07 //</span>
            <span>THE PHARMACOVIGILANCE CREED</span>
          </div>
          <span className="font-mono-code text-xs text-neutral-400 uppercase hidden sm:inline">EPIDEMIOLOGICAL INTEGRITY</span>
        </div>

        {/* Oversized Statement */}
        <div className="max-w-5xl mb-20 md:mb-32">
          <span className="font-mono-code text-xs text-[#FF3E14] uppercase tracking-widest block mb-4">OUR UNCOMPROMISING DOCTRINE</span>
          <h2 className="font-display font-extrabold text-4xl sm:text-6xl md:text-7xl lg:text-8xl leading-[0.98] tracking-[-0.04em] text-white">
            WE DO NOT COMPROMISE ON CLINICAL TRUTH. WE ARCHITECT THE REGULATORY STANDARD<span className="text-[#FF3E14]">.</span>
          </h2>
        </div>

        {/* 3 Pillars Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 lg:gap-16 pt-8 border-t border-white/15">
          {principles.map((item, idx) => (
            <div key={idx} className="flex flex-col">
              <span className="font-mono-code text-sm text-[#FF3E14] font-bold mb-4">
                {item.num}
              </span>
              <h3 className="font-display font-bold text-2xl lg:text-3xl tracking-tight text-white mb-4">
                {item.title}
              </h3>
              <p className="text-base text-neutral-400 leading-relaxed font-normal">
                {item.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Multidisciplinary Team Presence */}
        <div className="mt-28 md:mt-36 p-8 md:p-14 rounded-3xl border border-white/15 bg-white/[0.03] backdrop-blur-sm grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-8">
            <span className="font-mono-code text-xs text-neutral-400 uppercase tracking-widest block mb-2">AUTONOMOUS REGULATORY SURVEILLANCE</span>
            <h4 className="font-display font-bold text-2xl md:text-3xl text-white mb-3">
              Built for clinical pharmacovigilance teams, medical safety officers, and health authorities.
            </h4>
            <p className="text-neutral-400 text-sm md:text-base leading-relaxed">
              Vigil AI automates the mechanical drudgery of 2×2 contingency calculations, package insert text parsing, and literature searching, returning precious hours back to human safety scientists.
            </p>
          </div>

          <div className="lg:col-span-4 flex lg:justify-end">
            <a
              href="#workbench"
              className="inline-flex items-center gap-3 px-8 py-4 rounded-full bg-[#FF3E14] text-white font-mono-code text-xs uppercase tracking-widest font-bold hover:bg-white hover:text-[#121212] transition-colors duration-300 cursor-pointer"
            >
              <span>EXPLORE WORKBENCH</span>
              <ArrowUpRight className="w-4 h-4" />
            </a>
          </div>
        </div>

      </div>
    </section>
  );
}
