import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X, Sun, Moon } from 'lucide-react';

export default function Navbar({ isDark, onToggleTheme }) {
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
          ? 'py-4 bg-[#F5F2EB]/95 dark:bg-[#0C0C0D]/95 backdrop-blur-md border-b border-[#121212]/10 dark:border-white/10 shadow-xs' 
          : 'py-6 bg-transparent'
      }`}>
        <div className="max-w-[1720px] mx-auto px-6 md:px-12 flex items-center justify-between">
          
          {/* Brand Mark */}
          <a href="#" className="flex items-center gap-3">
            <span className="font-display font-extrabold text-2xl md:text-3xl tracking-tight text-[#121212] dark:text-[#F5F2EB]">
              VIGIL<span className="text-[#FF3E14]">.</span>
            </span>
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono-code uppercase tracking-wider bg-[#121212]/5 dark:bg-white/5 text-[#6E6C65] dark:text-[#9E9C96] border border-[#121212]/10 dark:border-white/10">
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
                className="font-mono-code text-xs uppercase tracking-wider text-[#121212]/70 dark:text-white/70 hover:text-[#121212] dark:hover:text-white transition-colors relative py-1"
              >
                {link.label}
              </a>
            ))}
          </nav>

          {/* Actions: Theme Toggle + Search Shortcut */}
          <div className="flex items-center gap-3">
            {/* Dark Mode Toggle Button */}
            <button
              type="button"
              onClick={onToggleTheme}
              className="p-2 rounded-full border border-[#121212]/15 dark:border-white/15 text-[#121212] dark:text-[#F5F2EB] hover:bg-[#121212]/5 dark:hover:bg-white/10 transition-colors cursor-pointer"
              title={isDark ? "Switch to light mode" : "Switch to dark mode"}
              aria-label="Toggle theme"
            >
              {isDark ? (
                <Sun className="w-4 h-4 text-amber-400" />
              ) : (
                <Moon className="w-4 h-4 text-[#121212]" />
              )}
            </button>

            <a
              href="#workbench"
              className="px-4 py-2 rounded-full border border-[#121212]/20 dark:border-white/20 font-mono-code text-xs uppercase tracking-wider text-[#121212] dark:text-white hover:bg-[#121212] hover:text-[#F5F2EB] dark:hover:bg-white dark:hover:text-[#0C0C0D] transition-colors"
            >
              TRY SEARCH
            </a>

            {/* Mobile Trigger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-[#121212] dark:text-white hover:bg-[#121212]/5 dark:hover:bg-white/10 cursor-pointer"
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
            className="fixed inset-0 z-40 bg-[#F5F2EB] dark:bg-[#0C0C0D] pt-24 px-8 flex flex-col justify-between pb-10 md:hidden"
          >
            <div className="flex flex-col gap-6">
              {navLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="font-display font-bold text-3xl text-[#121212] dark:text-[#F5F2EB]"
                >
                  {link.label}
                </a>
              ))}
            </div>

            <div className="border-t border-[#121212]/10 dark:border-white/10 pt-4 flex items-center justify-between font-mono-code text-xs text-[#6E6C65] dark:text-[#9E9C96]">
              <span>Vigil AI &middot; Pharmacovigilance Demo</span>
              <button
                type="button"
                onClick={onToggleTheme}
                className="flex items-center gap-1.5 p-1.5 rounded-md border border-[#121212]/15 dark:border-white/15"
              >
                {isDark ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5" />}
                <span>{isDark ? "Light" : "Dark"}</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
