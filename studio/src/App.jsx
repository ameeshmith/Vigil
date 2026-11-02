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

  return (
    <div className="relative min-h-screen bg-[#F5F2EB] text-[#121212] selection:bg-[#121212] selection:text-[#F5F2EB]">
      {/* Interactive Custom Cursor */}
      <CustomCursor />

      {/* Global Minimalist Navigation */}
      <Navbar />

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
