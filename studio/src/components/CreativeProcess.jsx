import React from 'react';
import { Filter, BrainCircuit, Cpu, ShieldCheck } from 'lucide-react';
import { processSteps } from '../data/vigilData';

export default function CreativeProcess() {
  const icons = [Filter, BrainCircuit, Cpu, ShieldCheck];

  return (
    <section id="process" className="relative py-20 md:py-32 border-t border-[#121212]/10 bg-[#ECE8DE]/30">
      <div className="max-w-[1720px] mx-auto px-6 md:px-12">
        
        {/* Section Header Tag */}
        <div className="flex items-center justify-between border-b border-[#121212]/10 pb-4 mb-12">
          <div className="flex items-center gap-2 font-mono-code text-xs uppercase tracking-wider text-[#6E6C65]">
            <span className="text-[#FF3E14] font-bold">04 //</span>
            <span>PIPELINE</span>
          </div>
          <span className="font-mono-code text-xs text-[#6E6C65] uppercase hidden sm:inline">LANGGRAPH AGENT FLOW</span>
        </div>

        {/* Headline */}
        <div className="max-w-3xl mb-12">
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl md:text-5xl tracking-tight text-[#121212]">
            The Investigation Pipeline<span className="text-[#FF3E14]">.</span>
          </h2>
          <p className="mt-3 text-[#121212]/70 text-base">
            How the LangGraph agent moves from a user's drug query to a verified safety assessment.
          </p>
        </div>

        {/* 4-Step Clean Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {processSteps.map((step, idx) => {
            const Icon = icons[idx] || Cpu;
            return (
              <div 
                key={step.phase}
                className="p-6 rounded-2xl bg-white border border-[#121212]/10 flex flex-col justify-between shadow-xs"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <span className="font-mono-code text-xs text-[#FF3E14] font-bold">
                      {step.phase}
                    </span>
                    <div className="w-8 h-8 rounded-full bg-[#F5F2EB] flex items-center justify-center">
                      <Icon className="w-4 h-4 text-[#121212]" />
                    </div>
                  </div>

                  <h3 className="font-display font-bold text-lg text-[#121212] mb-2">
                    {step.title}
                  </h3>

                  <p className="text-xs text-[#121212]/75 leading-relaxed font-sans">
                    {step.desc}
                  </p>
                </div>

                <div className="pt-4 mt-6 border-t border-[#121212]/5 font-mono-code text-[11px] text-[#6E6C65]">
                  STEP 0{idx + 1}
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
}
