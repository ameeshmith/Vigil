import React, { useState, useEffect } from 'react';
import Lenis from 'lenis';

import Navbar from './components/Navbar';
import CustomCursor from './components/CustomCursor';
import Hero from './components/Hero';
import Workbench from './components/Workbench';
import Introduction from './components/Introduction';
import FeaturedProjects from './components/FeaturedProjects';
import CreativeProcess from './components/CreativeProcess';
import Footer from './components/Footer';

export default function App() {
  const [activeDrugForWorkbench, setActiveDrugForWorkbench] = useState('');
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('vigil_theme');
    if (saved) return saved === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('vigil_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('vigil_theme', 'light');
    }
  }, [isDark]);

  useEffect(() => {
    // Initialize Lenis smooth scroll
    const lenis = new Lenis({
      duration: 1.0,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: 'vertical',
      smoothWheel: true
    });

    function raf(time) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);

    return () => {
      lenis.destroy();
    };
  }, []);

  const handleTriggerDrug = (drugName) => {
    setActiveDrugForWorkbench(drugName);
  };

  const toggleTheme = () => {
    setIsDark(prev => !prev);
  };

  return (
    <div className="relative min-h-screen bg-[#F5F2EB] dark:bg-[#0C0C0D] text-[#121212] dark:text-[#F5F2EB] selection:bg-[#121212] dark:selection:bg-[#F5F2EB] selection:text-[#F5F2EB] dark:selection:text-[#0C0C0D] transition-colors duration-300">
      {/* Interactive Custom Cursor */}
      <CustomCursor />

      {/* Global Minimalist Navigation with Theme Toggle */}
      <Navbar isDark={isDark} onToggleTheme={toggleTheme} />

      {/* Main Vigil AI Content Stack */}
      <main>
        {/* 01. Clean Typographic Hero with Search */}
        <Hero onSearchDrug={handleTriggerDrug} />

        {/* 02. Interactive Surveillance Workbench */}
        <Workbench 
          externalDrug={activeDrugForWorkbench} 
          onDrugProcessed={() => setActiveDrugForWorkbench('')} 
        />

        {/* 03. How It Works: Zero-Hallucination Tools */}
        <Introduction />

        {/* 04. Real-World Clinical Examples */}
        <FeaturedProjects onSelectDrug={handleTriggerDrug} />

        {/* 05. LangGraph Agent Pipeline */}
        <CreativeProcess />
      </main>

      {/* 06. Minimalist Colophon Footer */}
      <Footer />
    </div>
  );
}
