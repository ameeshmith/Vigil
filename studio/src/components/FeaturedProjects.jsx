import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import { drugCaseStudies } from '../data/vigilData';

export default function FeaturedProjects({ onSelectDrug }) {
  return (
    <section id="cases" className="relative py-20 md:py-32 border-t border-[#121212]/10 dark:border-white/10 bg-[#F5F2EB] dark:bg-[#0C0C0D]">
      <div className="max-w-[1720px] mx-auto px-6 md:px-12">
        
        {/* Section Header Tag */}
        <div className="flex items-center justify-between border-b border-[#121212]/10 dark:border-white/10 pb-4 mb-12">
          <div className="flex items-center gap-2 font-mono-code text-xs uppercase tracking-wider text-[#6E6C65] dark:text-[#9E9C96]">
            <span className="text-[#FF3E14] font-bold">03 //</span>
            <span>EXAMPLES</span>
          </div>
          <span className="font-mono-code text-xs text-[#6E6C65] dark:text-[#9E9C96] uppercase hidden sm:inline">REAL-WORLD DRUG INVESTIGATIONS</span>
        </div>

        {/* Section Headline */}
        <div className="max-w-3xl mb-12">
          <h2 className="font-display font-extrabold text-3xl sm:text-4xl md:text-5xl tracking-tight text-[#121212] dark:text-[#F5F2EB]">
            What Vigil AI Discovers<span className="text-[#FF3E14]">.</span>
          </h2>
          <p className="mt-3 text-[#121212]/70 dark:text-white/70 text-base">
            Examples of how statistical signals contrast against official FDA drug label sections.
          </p>
        </div>

        {/* Clean 3-Card Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {drugCaseStudies.map((caseStudy) => (
            <div 
              key={caseStudy.id}
              className="p-6 rounded-2xl bg-white dark:bg-[#151518] border border-[#121212]/10 dark:border-white/10 flex flex-col justify-between shadow-xs hover:border-[#121212] dark:hover:border-white/30 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between text-xs font-mono-code mb-3">
                  <span className="text-[#FF3E14] font-bold">{caseStudy.category}</span>
                  <span className="text-[#6E6C65] dark:text-[#9E9C96]">{caseStudy.reports}</span>
                </div>

                <h3 className="font-display font-bold text-2xl text-[#121212] dark:text-[#F5F2EB] mb-1">
                  {caseStudy.drug}
                </h3>
                <div className="text-xs font-mono-code text-[#6E6C65] dark:text-[#9E9C96] mb-4">
                  {caseStudy.headline}
                </div>

                <p className="text-sm text-[#121212]/75 dark:text-white/75 leading-relaxed mb-6 font-sans">
                  {caseStudy.summary}
                </p>
              </div>

              <div>
                <div className="p-3 rounded-lg bg-[#F5F2EB] dark:bg-[#1D1D22] text-xs font-mono mb-4 text-[#121212]/80 dark:text-[#F5F2EB]">
                  <div>PRR: <strong>{caseStudy.prr}</strong> &middot; Chi²: <strong>{caseStudy.chiSquare}</strong></div>
                  <div className="truncate text-[#6E6C65] dark:text-[#9E9C96] mt-1">{caseStudy.citation}</div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    if (onSelectDrug) onSelectDrug(caseStudy.queryDrug);
                    const el = document.getElementById('workbench');
                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="w-full py-2.5 rounded-lg border border-[#121212]/15 dark:border-white/15 text-xs font-mono-code uppercase font-semibold text-[#121212] dark:text-[#F5F2EB] hover:bg-[#121212] dark:hover:bg-white hover:text-white dark:hover:text-black transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <span>LOAD THIS DRUG</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}
