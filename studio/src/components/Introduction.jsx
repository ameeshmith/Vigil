import React from 'react';
import { Database, Calculator, ShieldCheck } from 'lucide-react';

export default function Introduction() {
  return (
    <section id="about" className="relative py-20 md:py-32 border-t border-[#121212]/10 dark:border-white/10 overflow-hidden">
      <div className="max-w-[1720px] mx-auto px-6 md:px-12">
        
        {/* Section Header Tag */}
        <div className="flex items-center justify-between border-b border-[#121212]/10 dark:border-white/10 pb-4 mb-12">
          <div className="flex items-center gap-2 font-mono-code text-xs uppercase tracking-wider text-[#6E6C65] dark:text-[#9E9C96]">
            <span className="text-[#FF3E14] font-bold">02 //</span>
            <span>HOW IT WORKS</span>
          </div>
          <span className="font-mono-code text-xs text-[#6E6C65] dark:text-[#9E9C96] uppercase hidden sm:inline">ZERO-MATH HALLUCINATIONS</span>
        </div>

        {/* Asymmetric Headline & Clean Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          
          {/* Left Column: Clear Headline */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            <h2 className="font-display font-extrabold text-3xl sm:text-4xl md:text-5xl lg:text-6xl leading-[1.05] tracking-tight text-[#121212] dark:text-[#F5F2EB]">
              AGENTIC REASONING WITH <span className="underline decoration-[#FF3E14] decoration-2 underline-offset-6">DETERMINISTIC</span> TOOLS.
            </h2>

            <div className="text-base md:text-lg text-[#121212]/75 dark:text-white/75 leading-relaxed space-y-4">
              <p>
                Language models often invent numbers when doing math. In drug safety, statistical accuracy is critical. Vigil AI strictly separates planning from calculation: the LLM plans the investigation, but all calculations run in Python tools.
              </p>
              <p>
                The agent queries public openFDA FAERS adverse event reports, computes Evans disproportionality metrics (PRR, ROR, Chi-square), checks approved FDA package inserts, and pulls relevant PubMed papers when an unlabeled signal emerges.
              </p>
            </div>

            {/* Clean Highlight Badges */}
            <div className="flex flex-wrap gap-2.5 pt-2">
              <span className="px-3.5 py-1.5 rounded-full border border-[#121212]/10 dark:border-white/10 bg-[#ECE8DE]/60 dark:bg-[#151518] text-xs font-mono-code text-[#121212] dark:text-[#F5F2EB] flex items-center gap-2">
                <Database className="w-3.5 h-3.5 text-[#FF3E14]" />
                openFDA FAERS Reports
              </span>
              <span className="px-3.5 py-1.5 rounded-full border border-[#121212]/10 dark:border-white/10 bg-[#ECE8DE]/60 dark:bg-[#151518] text-xs font-mono-code text-[#121212] dark:text-[#F5F2EB] flex items-center gap-2">
                <Calculator className="w-3.5 h-3.5 text-[#121212] dark:text-[#F5F2EB]" />
                Python Disproportionality Stats
              </span>
              <span className="px-3.5 py-1.5 rounded-full border border-[#121212]/10 dark:border-white/10 bg-[#ECE8DE]/60 dark:bg-[#151518] text-xs font-mono-code text-[#121212] dark:text-[#F5F2EB] flex items-center gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                Human Review Gate (HITL)
              </span>
            </div>
          </div>

          {/* Right Column: Clean Pill Card */}
          <div className="lg:col-span-5 relative mt-4 lg:mt-0">
            <div className="p-8 rounded-2xl bg-white dark:bg-[#151518] border border-[#121212]/10 dark:border-white/10 shadow-xs space-y-4">
              <div className="font-mono-code text-xs text-[#FF3E14] uppercase tracking-wider font-bold">
                THE EVANS CRITERIA STANDARD
              </div>
              <p className="font-sans text-sm text-[#121212]/80 dark:text-white/80 leading-relaxed">
                A statistical signal is flagged when all three criteria are met:
              </p>
              <ul className="space-y-2 font-mono text-xs text-[#121212] dark:text-[#F5F2EB] pt-2">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#FF3E14]" />
                  <span>Proportional Reporting Ratio (PRR) &ge; 2.0</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#FF3E14]" />
                  <span>Case count (a) &ge; 3 reports</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#FF3E14]" />
                  <span>Yates' corrected Chi-Square (&chi;&sup2;) &ge; 4.0</span>
                </li>
              </ul>
              <div className="pt-4 border-t border-[#121212]/10 dark:border-white/10 text-xs text-[#6E6C65] dark:text-[#9E9C96] font-sans">
                Computed via FastMCP tools. The LLM never touches the raw math.
              </div>
            </div>
          </div>

        </div>

      </div>
    </section>
  );
}
