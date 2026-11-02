import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, ArrowRight, ArrowDown } from 'lucide-react';

export default function Hero({ onSearchDrug }) {
  const [inputDrug, setInputDrug] = useState('');

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.05
      }
    }
  };

  const lineVariants = {
    hidden: { y: "80%", opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        duration: 0.8,
        ease: [0.16, 1, 0.3, 1]
      }
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputDrug.trim()) return;
    if (onSearchDrug) {
      onSearchDrug(inputDrug.trim());
      const el = document.getElementById('workbench');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleChipClick = (drugName) => {
    setInputDrug(drugName);
    if (onSearchDrug) {
      onSearchDrug(drugName);
      const el = document.getElementById('workbench');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section className="relative min-h-[90vh] pt-32 pb-16 md:pt-40 md:pb-24 flex flex-col justify-between overflow-hidden">
      
      {/* Background Subtle Dot Grid */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.03] bg-[radial-gradient(#121212_1px,transparent_1px)] [background-size:28px_28px]" />

      <div className="max-w-[1720px] mx-auto px-6 md:px-12 w-full relative z-10 flex-1 flex flex-col justify-between">
        
        {/* Top Minimal Ticker */}
        <div className="flex items-center justify-between border-b border-[#121212]/10 pb-4 mb-8 font-mono-code text-xs uppercase tracking-wider text-[#6E6C65]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF3E14]" />
            <span className="text-[#121212] font-semibold">AGENTIC DRUG SAFETY</span>
            <span className="text-[#6E6C65]/60">&mdash;</span>
            <span className="hidden sm:inline">PUBLIC FDA & PUBMED DATA</span>
          </div>
          <span className="text-[#6E6C65]">RESEARCH PROTOTYPE</span>
        </div>

        {/* Giant Hero Typography (carefully scaled so it NEVER wraps or truncates) */}
        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="my-auto py-4"
        >
          {/* Line 1 */}
          <div className="overflow-hidden">
            <motion.h1 
              variants={lineVariants}
              className="font-display font-extrabold text-5xl sm:text-7xl md:text-8xl lg:text-[7.5vw] leading-[0.95] tracking-[-0.04em] text-[#121212] flex items-center flex-wrap gap-x-3 md:gap-x-6"
            >
              <span>VIGIL</span>
              <span className="inline-block relative w-[14vw] sm:w-[12vw] h-[5vw] sm:h-[4.5vw] rounded-full overflow-hidden border border-[#121212]/20 my-auto shadow-inner">
                <img 
                  src="https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80" 
                  alt="Medicine" 
                  className="w-full h-full object-cover grayscale"
                />
              </span>
              <span>AI<span className="text-[#FF3E14]">.</span></span>
            </motion.h1>
          </div>

          {/* Line 2 */}
          <div className="overflow-hidden mt-1 md:mt-2">
            <motion.h1 
              variants={lineVariants}
              className="font-display font-extrabold text-5xl sm:text-7xl md:text-8xl lg:text-[7.5vw] leading-[0.95] tracking-[-0.04em] text-[#121212] flex items-center flex-wrap gap-x-3 md:gap-x-6"
            >
              <span className="text-[#FF3E14] italic font-normal tracking-[-0.02em] font-sans">AGENTIC</span>
              <span>DRUG</span>
            </motion.h1>
          </div>

          {/* Line 3 */}
          <div className="overflow-hidden mt-1 md:mt-2">
            <motion.h1 
              variants={lineVariants}
              className="font-display font-extrabold text-5xl sm:text-7xl md:text-8xl lg:text-[7.5vw] leading-[0.95] tracking-[-0.04em] text-[#121212]"
            >
              SAFETY<span className="text-[#FF3E14]">.</span>
            </motion.h1>
          </div>
        </motion.div>

        {/* Bottom Hero Layout: Simple description & direct search input */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-end border-t border-[#121212]/10 pt-8 mt-6">
          
          {/* Column 1: Clean summary */}
          <div className="md:col-span-5">
            <p className="font-sans text-base md:text-lg text-[#121212]/80 leading-relaxed">
              An AI safety scientist built with LangGraph. It analyzes openFDA adverse events, calculates disproportionality statistics in Python tools (never in the LLM), and cross-checks FDA drug labels.
            </p>
          </div>

          {/* Column 2: Fast Search Bar */}
          <div className="md:col-span-5">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6E6C65]" />
                <input
                  type="text"
                  value={inputDrug}
                  onChange={(e) => setInputDrug(e.target.value)}
                  placeholder="Enter a drug (e.g. Atorvastatin, Ozempic, Naxdom 250)..."
                  className="w-full pl-10 pr-4 py-3 bg-white border border-[#121212]/15 rounded-xl text-sm font-sans focus:outline-none focus:border-[#121212] transition-colors"
                />
              </div>
              <button
                type="submit"
                className="px-5 py-3 rounded-xl bg-[#121212] text-[#F5F2EB] font-mono-code text-xs uppercase tracking-wider font-semibold hover:bg-[#FF3E14] transition-colors flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
              >
                <span>SEARCH</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </form>

            {/* Quick pre-fill chips */}
            <div className="flex flex-wrap items-center gap-1.5 mt-3 text-[11px] font-mono-code text-[#6E6C65]">
              <span>TRY:</span>
              {['Ozempic', 'Atorvastatin', 'Simvastatin', 'Naxdom 250'].map(d => (
                <button
                  key={d}
                  type="button"
                  onClick={() => handleChipClick(d)}
                  className="px-2 py-0.5 rounded bg-[#121212]/5 hover:bg-[#121212] hover:text-[#F5F2EB] border border-[#121212]/10 transition-colors cursor-pointer"
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* Column 3: Scroll Down Link */}
          <div className="md:col-span-2 flex md:justify-end">
            <a 
              href="#workbench" 
              className="inline-flex items-center gap-2 font-mono-code text-xs text-[#6E6C65] hover:text-[#121212] transition-colors"
            >
              <span>WORKBENCH</span>
              <ArrowDown className="w-3.5 h-3.5" />
            </a>
          </div>

        </div>

      </div>
    </section>
  );
}
