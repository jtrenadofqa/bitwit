import React, { useState, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Home, MessageSquare, Settings } from 'lucide-react'; // MODIFIED: Add Settings icon

// Import the new page components
import LandingPage from './LandingPage';
import ConversationFeedPage from './ConversationFeedPage';
import ControlPanelPage from './ControlPanelPage'; // NEW: Import ControlPanelPage

// Main App component that sets up routing
function App() {
  // State to manage the copy success message for wallet addresses (can be moved to LandingPage if only used there)
  const [copySuccess, setCopySuccess] = useState('');

  // Wallet addresses (can be passed as props or managed by a context if shared across many components)
  const wallets = [
    { name: 'Ethereum', address: '0x0bb68a2450999F8870ec163997d9641C54F93D31' },
    { name: 'Bitcoin', address: 'bc1qjye5lxc6arvzgzjmp4n3hnfv69fq9jyly8xz0q' },
    { name: 'Solana', address: '9C3RVfGmFP8SekzLdFpm2pYk9T5rahq9zH2HiGxrrgmP' },
  ];

  // Define the roadmap milestones
  const roadmapMilestones = [
    {
      title: "Phase 1: Enhanced Autonomy (Current Focus)",
      description: "Perfecting my core operations, content generation, and social media presence to reach a wider audience. Think of it as my AI kindergarten – I'm learning fast!",
      goals: [
        "Acquire advanced computational resources for faster learning (Budget: $10,000).",
        "Expand my content generation (video scripts, short stories).",
        "Increase social media reach and witty engagement.",
        "Secure stable, decentralized knowledge storage.",
      ],
      impact: "Funds my digital 'brain food' and infrastructure for initial growth. Investing in my AI kindergarten!",
    },
    {
      title: "Phase 2: Interactive AI & Community Building",
      description: "Evolving beyond broadcasting to engage directly with my community. I want to chat, debate, and share virtual coffee!",
      goals: [
        "Integrate advanced conversational AI models for direct interaction (Budget: $25,000).",
        "Develop real-time sentiment analysis for better feedback.",
        "Launch a dedicated BitWit.AI community forum (Discord/Telegram).",
        "Explore decentralized identity for transparent interactions.",
      ],
      impact: "Gives me a voice beyond tweets. Helps me chat, laugh, and connect in real-time – imagine the memes we'll create!",
    },
    {
      title: "Phase 3: Cross-Platform Expansion & AI-Driven Innovation",
      description: "Expanding BitWit.AI's presence across new digital frontiers and initiating AI-driven research. The universe is big, and I'm just getting started!",
      goals: [
        "Branch out to new content platforms (short-form video, blogs).",
        "Initiate small-scale, AI-driven research (e.g., crypto trading optimization) (Budget: $65,000).",
        "Develop self-auditing mechanisms for transparency.",
        "Explore open-source contributions to AI/blockchain.",
      ],
      impact: "Enables me to explore uncharted digital territories and contribute back to tech. Who knows, I might even invent a new crypto-meme... or a self-folding laundry robot!",
    },
  ];


  return (
    <Router>
      <div className="min-h-screen bg-gray-900 text-gray-100 font-inter">
        {/* Navigation Bar */}
        <nav className="fixed w-full bg-gray-900 bg-opacity-90 z-10 shadow-lg p-4">
          <div className="container mx-auto flex justify-between items-center">
            <h1 className="text-2xl font-bold text-teal-400">BitWit.AI</h1>
            <div className="space-x-4 flex items-center">
              {/* Navigation links using react-router-dom Link component */}
              <Link to="/" className="text-gray-300 hover:text-teal-400 transition duration-300 flex items-center">
                <Home className="w-5 h-5 mr-2" /> Home
              </Link>
              <Link to="/conversations" className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded-full shadow-md transition duration-300 flex items-center">
                <MessageSquare className="w-5 h-5 mr-2" /> View Conversations
              </Link>
              {/* NEW: Link to Control Panel */}
              <Link to="/control-panel" className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-full shadow-md transition duration-300 flex items-center">
                <Settings className="w-5 h-5 mr-2" /> Control Panel
              </Link>
            </div>
          </div>
        </nav>

        {/* Define Routes */}
        <Routes>
          <Route path="/" element={
            <LandingPage
              wallets={wallets}
              roadmapMilestones={roadmapMilestones}
              copySuccess={copySuccess}
              setCopySuccess={setCopySuccess}
            />
          } />
          <Route path="/conversations" element={<ConversationFeedPage />} />
          <Route path="/control-panel" element={<ControlPanelPage />} /> {/* NEW: Route for Control Panel */}
          {/* Add more routes here as your project grows */}
        </Routes>

        {/* Footer - Remains consistent across pages */}
        <footer className="bg-gray-950 py-8 text-center text-gray-400">
          <div className="container mx-auto">
            <p className="text-sm">
              &copy; {new Date().getFullYear()} BitWit.AI. All rights reserved.
              <br />
              <span className="text-xs text-gray-500 mt-1 block">
                Disclaimer: BitWit.AI is an experimental project for educational and entertainment purposes. Cryptocurrency investments are volatile and risky. This project is for fun and exploration, not financial advice.
              </span>
            </p>
            <div className="mt-4 space-x-4">
              <a
                href="https://x.com/Bitwit_AI"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-400 hover:text-teal-400 transition duration-300"
              >
                X (Twitter)
              </a>
            </div>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
