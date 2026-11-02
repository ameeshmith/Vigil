import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, CheckCircle2, Mail, ShieldCheck, Database } from 'lucide-react';

export default function Contact() {
  const [selectedDiscipline, setSelectedDiscipline] = useState('Post-Marketing Surveillance');
  const [drugTarget, setDrugTarget] = useState('');
  const [email, setEmail] = useState('');
  const [notes, setNotes] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const disciplines = [
    'Post-Marketing Surveillance',
    'Labeling Discrepancy Audit',
    'Automated FAERS Pipeline',
    'Regulatory Strategy',
    'Target Literature Synthesis'
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setDrugTarget('');
      setEmail('');
      setNotes('');
    }, 6000);
  };

  return (
    <section id="contact" className="relative py-28 md:py-44 border-t border-[#121212]/15 bg-[#F5F2EB]">
      <div className="max-w-[1720px] mx-auto px-6 md:px-12">
        
        {/* Section Header Tag */}
        <div className="flex items-center justify-between border-b border-[#121212]/15 pb-6 mb-16 md:mb-24">
          <div className="flex items-center gap-3 font-mono-code text-xs uppercase tracking-widest text-[#6E6C65]">
            <span className="text-[#FF3E14] font-bold">09 //</span>
            <span>CLINICAL SURVEILLANCE INQUIRIES</span>
          </div>
          <span className="font-mono-code text-xs text-[#6E6C65] uppercase hidden sm:inline">INSTITUTIONAL PARTNERSHIPS</span>
        </div>

        {/* Big Provocative Headline */}
        <div className="max-w-5xl mb-20 md:mb-28">
          <h2 className="font-display font-extrabold text-5xl sm:text-6xl md:text-7xl lg:text-8xl leading-[0.94] tracking-[-0.05em] text-[#121212]">
            COMMISSION A TARGET <span className="text-[#FF3E14]">SAFETY AUDIT</span><span className="text-[#121212]">.</span>
          </h2>
        </div>

        {/* Contact Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start">
          
          {/* Left Column: Direct Info & Research Hubs */}
          <div className="lg:col-span-5 flex flex-col justify-between h-full">
            <div className="flex flex-col gap-10">
              <p className="text-lg md:text-xl text-[#121212]/80 leading-relaxed font-normal">
                Deploy Vigil AI for proprietary molecule dossiers, label expansion defense, or automated high-throughput pharmacovigilance screening.
              </p>

              <div className="flex flex-col gap-6 pt-4 border-t border-[#121212]/15 font-mono-code text-xs">
                <div className="flex items-center gap-4">
                  <Mail className="w-4 h-4 text-[#FF3E14]" />
                  <a href="mailto:surveillance@vigil-ai.io" className="text-base font-bold text-[#121212] hover:text-[#FF3E14] transition-colors underline">
                    surveillance@vigil-ai.io
                  </a>
                </div>

                <div className="flex items-center gap-4">
                  <Database className="w-4 h-4 text-[#FF3E14]" />
                  <span className="text-sm text-[#121212]">FAERS &middot; openFDA &middot; PubMed E-Utilities</span>
                </div>
              </div>

              {/* Research Coordinates */}
              <div className="grid grid-cols-3 gap-4 pt-6 border-t border-[#121212]/15">
                <div>
                  <div className="font-mono-code text-[10px] text-[#6E6C65] uppercase">ZURICH HUB</div>
                  <div className="font-display font-bold text-sm text-[#121212]">Gotthardstrasse 26</div>
                  <div className="font-mono-code text-[10px] text-[#6E6C65]">8002 Zürich</div>
                </div>
                <div>
                  <div className="font-mono-code text-[10px] text-[#6E6C65] uppercase">LONDON LAB</div>
                  <div className="font-display font-bold text-sm text-[#121212]">BioCity Campus</div>
                  <div className="font-mono-code text-[10px] text-[#6E6C65]">EC1M London</div>
                </div>
                <div>
                  <div className="font-mono-code text-[10px] text-[#6E6C65] uppercase">BOSTON BIOTECH</div>
                  <div className="font-display font-bold text-sm text-[#121212]">Kendall Square</div>
                  <div className="font-mono-code text-[10px] text-[#6E6C65]">02142 Cambridge</div>
                </div>
              </div>
            </div>

            <div className="pt-8 mt-12 border-t border-[#121212]/15 font-mono-code text-xs text-[#6E6C65]">
              STANDARD AUDIT REPORT TURNAROUND: &lt; 24 HOURS
            </div>
          </div>

          {/* Right Column: Interactive Brief Dispatcher */}
          <div className="lg:col-span-7 bg-[#ECE8DE]/60 p-8 md:p-12 rounded-3xl border border-[#121212]/15 shadow-sm">
            {submitted ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="py-16 text-center flex flex-col items-center justify-center"
              >
                <div className="w-16 h-16 rounded-full bg-[#121212] text-[#F5F2EB] flex items-center justify-center mb-6">
                  <CheckCircle2 className="w-8 h-8 text-[#FF3E14]" />
                </div>
                <h3 className="font-display font-bold text-3xl text-[#121212] mb-3">
                  SURVEILLANCE DIRECTIVE QUEUED
                </h3>
                <p className="text-[#121212]/70 max-w-md mx-auto text-sm leading-relaxed font-mono">
                  Our clinical pharmacovigilance lead will review the molecule parameters and dispatch the validated disproportionality dossier.
                </p>
              </motion.div>
            ) : (
              <form onSubmit={handleSubmit} className="flex flex-col gap-8">
                {/* Discipline Selector */}
                <div>
                  <label className="block font-mono-code text-xs uppercase tracking-wider text-[#6E6C65] mb-3 font-semibold">
                    01 // SELECT CLINICAL DISCIPLINE
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {disciplines.map(d => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => setSelectedDiscipline(d)}
                        className={`px-4 py-2.5 rounded-full text-xs font-mono-code uppercase tracking-wider transition-all cursor-pointer ${
                          selectedDiscipline === d
                            ? 'bg-[#121212] text-[#F5F2EB] font-bold shadow-md'
                            : 'bg-[#F5F2EB] text-[#121212]/70 border border-[#121212]/15 hover:border-[#121212]'
                        }`}
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Target Drug & Email Row */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block font-mono-code text-xs uppercase tracking-wider text-[#6E6C65] mb-2 font-semibold">
                      02 // TARGET DRUG / MOLECULE
                    </label>
                    <input
                      type="text"
                      required
                      value={drugTarget}
                      onChange={(e) => setDrugTarget(e.target.value)}
                      placeholder="e.g. Semaglutide, Atorvastatin..."
                      className="w-full p-4 rounded-xl bg-[#F5F2EB] border border-[#121212]/15 text-sm font-sans focus:outline-none focus:border-[#121212]"
                    />
                  </div>

                  <div>
                    <label className="block font-mono-code text-xs uppercase tracking-wider text-[#6E6C65] mb-2 font-semibold">
                      03 // INSTITUTIONAL EMAIL
                    </label>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="safety-officer@pharma.com"
                      className="w-full p-4 rounded-xl bg-[#F5F2EB] border border-[#121212]/15 text-sm font-sans focus:outline-none focus:border-[#121212]"
                    />
                  </div>
                </div>

                {/* Clinical Notes */}
                <div>
                  <label className="block font-mono-code text-xs uppercase tracking-wider text-[#6E6C65] mb-2 font-semibold">
                    04 // CLINICAL SCOPE & SPECIFIC MEDDRA PRIORITIES
                  </label>
                  <textarea
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Specify whether looking for specific organ toxicities (e.g. hepatotoxicity, pancreatitis), comparative competitor benchmarks, or historical label evolution..."
                    className="w-full p-4 rounded-xl bg-[#F5F2EB] border border-[#121212]/15 text-sm font-sans focus:outline-none focus:border-[#121212]"
                  />
                </div>

                {/* Submit button */}
                <button
                  type="submit"
                  className="w-full py-5 rounded-xl bg-[#121212] text-[#F5F2EB] font-mono-code text-xs uppercase tracking-widest font-bold hover:bg-[#FF3E14] transition-colors duration-300 flex items-center justify-center gap-2 cursor-pointer shadow-md"
                >
                  <span>DISPATCH CLINICAL AUDIT DIRECTIVE</span>
                  <ArrowUpRight className="w-4 h-4" />
                </button>
              </form>
            )}
          </div>

        </div>

      </div>
    </section>
  );
}
