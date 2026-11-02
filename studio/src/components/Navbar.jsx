import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X } from 'lucide-react';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 30);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { label: "WORKBENCH", href: "#workbench" },
    { label: "HOW IT WORKS", href: "#about" },
    { label: "EXAMPLES", href: "#cases" },
    { label: "PIPELINE", href: "#process" }
  ];

  return (
    <>
      <header className={`fixed top-0 left-0 w-full z-50 transition-all duration-300 ${
        scrolled 
          ? 'py-4 bg-[#F5F2EB]/95 backdrop-blur-md border-b border-[#121212]/10 shadow-xs' 
          : 'py-6 bg-transparent'
      }`}>
        <div className="max-w-[1720px] mx-auto px-6 md:px-12 flex items-center justify-between">
          
          {/* Brand Mark */}
          <a href="#" className="flex items-center gap-3">
            <span className="font-display font-extrabold text-2xl md:text-3xl tracking-tight text-[#121212]">
              VIGIL<span className="text-[#FF3E14]">.</span>
            </span>
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono-code uppercase tracking-wider bg-[#121212]/5 text-[#6E6C65] border border-[#121212]/10">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              DEMO MODE
            </span>
          </a>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="font-mono-code text-xs uppercase tracking-wider text-[#121212]/70 hover:text-[#121212] transition-colors relative py-1"
              >
                {link.label}
              </a>
            ))}
          </nav>

          {/* Minimal Status indicator */}
          <div className="flex items-center gap-4">
            <a
              href="#workbench"
              className="px-4 py-2 rounded-full border border-[#121212]/20 font-mono-code text-xs uppercase tracking-wider text-[#121212] hover:bg-[#121212] hover:text-[#F5F2EB] transition-colors"
            >
              TRY SEARCH
            </a>

            {/* Mobile Trigger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-[#121212] hover:bg-[#121212]/5 cursor-pointer"
              aria-label="Toggle Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

        </div>
      </header>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="fixed inset-0 z-40 bg-[#F5F2EB] pt-24 px-8 flex flex-col justify-between pb-10 md:hidden"
          >
            <div className="flex flex-col gap-6">
              {navLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="font-display font-bold text-3xl text-[#121212]"
                >
                  {link.label}
                </a>
              ))}
            </div>

            <div className="border-t border-[#121212]/10 pt-4 font-mono-code text-xs text-[#6E6C65]">
              Vigil AI &middot; Pharmacovigilance Demo
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
