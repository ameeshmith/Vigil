import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Minus } from 'lucide-react';
import { capabilities } from '../data/vigilData';

export default function Capabilities() {
  const [activeIdx, setActiveIdx] = useState(0);

  return (
    <section id="capabilities" className="relative py-28 md:py-44 border-t border-[#121212]/15 bg-[#F5F2EB]">
      <div className="max-w-[1720px] mx-auto px-6 md:px-12">
        
        {/* Section Header Tag */}
        <div className="flex items-center justify-between border-b border-[#121212]/15 pb-6 mb-16 md:mb-24">
          <div className="flex items-center gap-3 font-mono-code text-xs uppercase tracking-widest text-[#6E6C65]">
            <span className="text-[#FF3E14] font-bold">04 //</span>
            <span>CORE AGENT DISCIPLINES</span>
          </div>
          <span className="font-mono-code text-xs text-[#6E6C65] uppercase hidden sm:inline">RIGOROUS STATISTICAL ARCHITECTURE</span>
        </div>

        {/* Section Headline */}
        <div className="max-w-4xl mb-16 md:mb-24">
          <h2 className="font-display font-extrabold text-4xl sm:text-5xl md:text-6xl lg:text-7xl leading-[1.02] tracking-[-0.04em] text-[#121212]">
            SCIENTIFIC RIGOR AT AGENTIC SCALE<span className="text-[#FF3E14]">.</span>
          </h2>
        </div>

        {/* Interactive Capability List with Image Reveal */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
          
          {/* Left Column: Capability Accordion List */}
          <div className="lg:col-span-7 flex flex-col border-t border-[#121212]/20">
            {capabilities.map((item, idx) => {
              const isActive = activeIdx === idx;
              return (
                <div 
                  key={item.number}
                  onMouseEnter={() => setActiveIdx(idx)}
                  onClick={() => setActiveIdx(idx)}
                  className={`border-b border-[#121212]/20 py-8 md:py-10 cursor-pointer transition-colors duration-300 group ${
                    isActive ? 'bg-[#ECE8DE]/50 px-4 -mx-4 rounded-xl' : 'hover:bg-[#ECE8DE]/20 px-0'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-baseline gap-6 md:gap-10">
                      <span className="font-mono-code text-xs md:text-sm text-[#FF3E14] font-bold">
                        {item.number}
                      </span>
                      <h3 className="font-display font-bold text-2xl sm:text-3xl md:text-4xl text-[#121212] tracking-tight group-hover:text-[#FF3E14] transition-colors">
                        {item.title}
                      </h3>
                    </div>
                    <div className="p-2 rounded-full border border-[#121212]/15 group-hover:border-[#121212] transition-colors shrink-0">
                      {isActive ? <Minus className="w-4 h-4 text-[#121212]" /> : <Plus className="w-4 h-4 text-[#6E6C65]" />}
                    </div>
                  </div>

                  <AnimatePresence>
                    {isActive && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                        className="overflow-hidden"
                      >
                        <div className="pt-6 pl-10 md:pl-16 pr-4">
                          <p className="text-base md:text-lg text-[#121212]/80 leading-relaxed mb-6 font-normal">
                            {item.description}
                          </p>

                          <div className="flex flex-wrap gap-2">
                            {item.tags.map(tag => (
                              <span 
                                key={tag}
                                className="px-3.5 py-1.5 rounded-full bg-[#121212] text-[#F5F2EB] text-xs font-mono-code uppercase tracking-wider"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>

          {/* Right Column: Dynamic Preview Screen */}
          <div className="lg:col-span-5 sticky top-32 hidden lg:block">
            <div className="relative rounded-3xl overflow-hidden aspect-[4/5] bg-[#ECE8DE] border border-[#121212]/15 shadow-2xl">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeIdx}
                  initial={{ opacity: 0, scale: 1.05 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                  className="w-full h-full relative"
                >
                  <img 
                    src={capabilities[activeIdx]?.image} 
                    alt={capabilities[activeIdx]?.title} 
                    className="w-full h-full object-cover grayscale contrast-110"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#121212]/90 via-[#121212]/30 to-transparent p-8 flex flex-col justify-end text-white">
                    <span className="font-mono-code text-xs uppercase tracking-widest text-[#FF3E14] mb-2">
                      DISCIPLINE {capabilities[activeIdx]?.number}
                    </span>
                    <h4 className="font-display font-bold text-2xl mb-2">
                      {capabilities[activeIdx]?.title}
                    </h4>
                    <p className="text-white/70 text-xs font-mono leading-relaxed">
                      Audited by FastMCP Micro-tools &amp; LangGraph State Validation.
                    </p>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>

        </div>

      </div>
    </section>
  );
}
