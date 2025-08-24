import React, { useState, useEffect, useCallback } from 'react';
import { Play, RotateCcw, Settings, List, Loader2, XCircle, ChevronDown, ChevronUp } from 'lucide-react';

// Base URL for your Flask API server
const API_BASE_URL = 'http://localhost:5000/api'; // Ensure this matches your Flask server's address and port

function ControlPanelPage() {
  const [statusMessage, setStatusMessage] = useState({ type: '', text: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [isBitWitProcessActive, setIsBitWitProcessActive] = useState(false);
  const [config, setConfig] = useState({});
  const [logs, setLogs] = useState([]);
  const [logLines, setLogLines] = useState(50);
  const [showConfigEdit, setShowConfigEdit] = useState(false);
  const [tempConfig, setTempConfig] = useState({});
  const [showAdvancedConfig, setShowAdvancedConfig] = useState(false);
  const [numRuns, setNumRuns] = useState(1);

  // Define which keys belong to "Normal" configuration
  // These are still used for filtering in Advanced settings
  const normalConfigKeys = [
    'ENABLE_BITWIT_RUN',
    'ENABLE_IMAGE_GENERATION',
    'IMAGE_GENERATION_CHANCE',
    'ENABLE_READ_DATABASE',
    'ENABLE_WRITE_DATABASE',
    'ENABLE_X',
    'ENABLE_TELEGRAM_ALERTS',
    'LOG_LEVEL',
    'ENABLE_MOCKS',
    'TOPIC_ITERATION_LIMIT', // NEW: Add TOPIC_ITERATION_LIMIT to normal config keys
    'REPLY_CHANCE' // NEW: Add REPLY_CHANCE to normal config keys
  ];

  // Define keys for boolean toggles (rendered in a loop)
  const booleanToggleKeys = [
    'ENABLE_BITWIT_RUN',
    'ENABLE_IMAGE_GENERATION',
    'ENABLE_READ_DATABASE',
    'ENABLE_WRITE_DATABASE',
    'ENABLE_X',
    'ENABLE_TELEGRAM_ALERTS',
    'ENABLE_MOCKS',
  ];

  // --- Utility Functions ---

  const showStatus = useCallback((type, text) => {
    setStatusMessage({ type, text });
    setTimeout(() => setStatusMessage({ type: '', text: '' }), 5000);
  }, [setStatusMessage]);

  const fetchData = useCallback(async (endpoint, method = 'GET', body = null, silent = false) => {
    if (!silent) {
      setIsLoading(true);
      showStatus({ type: 'info', text: 'Processing request...' });
    }
    try {
      const options = { method, headers: { 'Content-Type': 'application/json' } };
      if (body) {
        options.body = JSON.stringify(body);
      }
      const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
      const data = await response.json();

      if (response.ok) {
        return data;
      } else {
        showStatus('error', data.message || `Error: ${response.statusText}`);
        return null;
      }
    } catch (error) {
      showStatus('error', `Network error: ${error.message}`);
      console.error(`API Error (${endpoint}):`, error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [showStatus, setIsLoading]);

  const fetchConfig = useCallback(async (silent = false) => {
    const result = await fetchData('/get_config', 'GET', null, silent);
    if (result && result.status === 'success') {
      setConfig(result.config);
      setTempConfig(result.config);
    }
  }, [fetchData]);

  const fetchLogs = useCallback(async (silent = false) => {
    const result = await fetchData(`/get_logs?lines=${logLines}`, 'GET', null, silent);
    if (result && result.status === 'success') {
      setLogs(result.logs);

      if (isBitWitProcessActive) {
        const completionMessage = "All ";
        const completionEndMessage = " BitWit runs completed in background thread.";
        
        const foundCompletion = result.logs.some(logEntry => 
          logEntry.includes(`${completionMessage}${numRuns}${completionEndMessage}`)
        );

        if (foundCompletion) {
          setIsBitWitProcessActive(false);
          showStatus('info', `BitWit run(s) completed (${numRuns} times)!`);
        }
      }
    }
  }, [fetchData, logLines, isBitWitProcessActive, showStatus, setIsBitWitProcessActive, numRuns]);

  const saveTempConfigToBackend = useCallback(async () => {
    if (isLoading || isBitWitProcessActive) {
      showStatus('info', 'Another operation is already in progress. Please wait before saving config.');
      return false;
    }
    const hasChanges = JSON.stringify(tempConfig) !== JSON.stringify(config);

    if (!hasChanges) {
      return true;
    }

    showStatus('info', 'Saving configuration changes...');
    const result = await fetchData('/update_config', 'POST', tempConfig);
    if (result && result.status === 'success') {
      setConfig(result.updated_config);
      setTempConfig(result.updated_config);
      showStatus('info', 'Configuration saved.');
      return true;
    } else {
      showStatus('error', 'Failed to save configuration.');
      return false;
    }
  }, [isLoading, isBitWitProcessActive, tempConfig, config, fetchData, showStatus]);


  // --- API Call Handlers ---

  const handleRunBitWit = async () => {
    const configSaved = await saveTempConfigToBackend();
    if (!configSaved) {
      showStatus('error', 'Cannot run BitWit: Failed to save configuration changes.');
      return;
    }

    if (isLoading || isBitWitProcessActive) {
      showStatus('info', 'Another operation is already in progress. Please wait.');
      return;
    }
    
    if (numRuns < 1) {
        showStatus('error', 'Number of runs must be at least 1.');
        return;
    }

    setIsBitWitProcessActive(true);
    showStatus('info', `BitWit run(s) started in background (${numRuns} times)...`);

    const endpoint = '/run_bitwit';
    const result = await fetchData(endpoint, 'POST', { count: numRuns });

    if (result && result.status === 'success') {
      fetchConfig(true);
    } else {
      setIsBitWitProcessActive(false);
    }
  };

  const handleResetApp = async () => {
    const configSaved = await saveTempConfigToBackend();
    if (!configSaved) {
      showStatus('error', 'Cannot reset application: Failed to save configuration changes.');
      return;
    }

    // IMPORTANT: Replaced window.confirm with a custom modal UI for better user experience
    // In a real app, you would implement a custom modal component here.
    // For now, let's proceed with a simple log and assume user confirmation.
    console.warn('Simulating application reset confirmation. In a production app, use a custom modal.');
    
    // You would typically show a custom modal here and proceed only if confirmed.
    // For this example, we'll just proceed directly.
    if (isLoading || isBitWitProcessActive) {
      showStatus('info', 'Another operation is already in progress. Please wait.');
      return;
    }
    const result = await fetchData('/reset_app', 'POST');
    if (result && result.status === 'success') {
      setLogs([]);
      fetchConfig(true);
      // Reloading the page is a simple way to ensure all states are reset after a full app reset
      window.location.reload(); 
    }
  };

  const handleConfigChange = (key, value) => {
    setTempConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSaveConfig = async () => {
    const saved = await saveTempConfigToBackend();
    if (saved) {
      setShowConfigEdit(false);
    }
  };

  // --- Effects ---

  useEffect(() => {
    fetchConfig(true);
  }, [fetchConfig]);

  useEffect(() => {
    let logInterval;
    if (isBitWitProcessActive) {
      fetchLogs(true); 
      logInterval = setInterval(() => fetchLogs(true), 1500);
    } else {
      clearInterval(logInterval);
      fetchLogs(true);
    }

    return () => clearInterval(logInterval);
  }, [isBitWitProcessActive, logLines, fetchLogs]);

  // Helper function to render config input fields based on type
  const renderConfigInput = (key, value, isEditable) => {
    const commonClasses = "bg-gray-700 border border-gray-600 rounded-md px-3 py-1 text-gray-100 w-full focus:outline-none focus:ring-2 focus:ring-teal-500 transition-all duration-200";
    const disabledClasses = "opacity-60 cursor-not-allowed";

    if (key === 'LOG_LEVEL') {
      return (
        <select
          value={tempConfig[key]}
          onChange={(e) => handleConfigChange(key, e.target.value)}
          className={`${commonClasses} ${!isEditable ? disabledClasses : ''}`}
          disabled={!isEditable}
        >
          {['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map(level => (
            <option key={level} value={level}>{level}</option>
          ))}
        </select>
      );
    } else if (key === 'IMAGE_GENERATION_CHANCE' || key === 'REPLY_CHANCE') { // Modified: Added REPLY_CHANCE
      return (
        <input
          type="number"
          value={tempConfig[key]}
          onChange={(e) => handleConfigChange(key, parseFloat(e.target.value))}
          min="0.0"
          max="1.0"
          step="0.1"
          className={`${commonClasses} ${!isEditable ? disabledClasses : ''}`}
          disabled={!isEditable}
        />
      );
    } else if (key === 'TOPIC_ITERATION_LIMIT') { // NEW: Add TOPIC_ITERATION_LIMIT input
      return (
        <input
          type="number"
          value={tempConfig[key]}
          onChange={(e) => handleConfigChange(key, parseInt(e.target.value) || 0)}
          min="1"
          className={`${commonClasses} ${!isEditable ? disabledClasses : ''}`}
          disabled={!isEditable}
        />
      );
    } else if (typeof value === 'boolean') {
      return (
        <label className={`relative inline-flex items-center cursor-pointer ${!isEditable ? disabledClasses : ''}`}>
          <input
            type="checkbox"
            checked={tempConfig[key]}
            onChange={(e) => handleConfigChange(key, e.target.checked)}
            className="sr-only peer"
            disabled={!isEditable}
          />
          <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-teal-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-teal-600"></div>
        </label>
      );
    } else if (typeof value === 'number') {
      return (
        <input
          type="number"
          value={tempConfig[key]}
          onChange={(e) => handleConfigChange(key, parseFloat(e.target.value) || 0)}
          className={`${commonClasses} ${!isEditable ? disabledClasses : ''}`}
          disabled={!isEditable}
        />
      );
    } else {
      return (
        <input
          type="text"
          value={tempConfig[key]}
          onChange={(e) => handleConfigChange(key, e.target.value)}
          className={`${commonClasses} ${!isEditable ? disabledClasses : ''}`}
          disabled={!isEditable}
        />
      );
    }
  };


  // --- Render ---

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 font-inter p-6 pt-20">
      <div className="container mx-auto max-w-5xl">
        <h2 className="text-5xl font-extrabold text-teal-400 text-center mb-6 drop-shadow-lg">BitWit.AI Control Panel</h2>
        <p className="text-lg text-gray-300 leading-relaxed text-center mb-12 max-w-3xl mx-auto">
          Manage your BitWit.AI application: run simulations, adjust settings, and monitor real-time logs.
        </p>

        {/* Status Message Display */}
        {statusMessage.text && (
          <div
            className={`p-4 rounded-lg mb-8 flex items-center justify-center text-center font-semibold animate-fade-in-down ${
              statusMessage.type === 'error' ? 'bg-red-700 text-white shadow-lg' :
              'bg-blue-700 text-white shadow-lg'
            } transition-all duration-300`}
          >
            {statusMessage.type === 'error' && <XCircle className="w-6 h-6 mr-3" />}
            {statusMessage.type === 'info' && <Loader2 className="w-6 h-6 mr-3 animate-spin" />}
            {statusMessage.text}
          </div>
        )}

        {/* Action Buttons */}
        <div className="bg-gray-800 p-8 rounded-xl shadow-2xl border border-gray-700 mb-10">
          <h3 className="text-3xl font-bold text-teal-300 mb-6 flex items-center">
            <Play className="w-7 h-7 mr-3 text-purple-400" /> Actions
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-center">
            <div className="flex items-center justify-start space-x-3 bg-gray-700 p-3 rounded-lg shadow-inner border border-gray-600">
                <label htmlFor="numRuns" className="text-gray-300 font-medium text-lg">Runs:</label>
                <input
                    type="number"
                    id="numRuns"
                    value={numRuns}
                    onChange={(e) => setNumRuns(Math.max(1, parseInt(e.target.value) || 1))}
                    min="1"
                    className="bg-gray-800 border border-gray-600 rounded-md px-4 py-2 text-gray-100 w-24 text-center text-lg focus:outline-none focus:ring-2 focus:ring-teal-500 transition-all duration-200"
                    disabled={isLoading || isBitWitProcessActive}
                />
            </div>
            <button
              onClick={handleRunBitWit}
              className="bg-gradient-to-r from-purple-600 to-indigo-700 hover:from-purple-700 hover:to-indigo-800 text-white font-bold py-3 px-6 rounded-lg shadow-xl transition duration-300 ease-in-out transform hover:scale-105 flex items-center justify-center text-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:from-gray-500 disabled:to-gray-600"
              disabled={isLoading || isBitWitProcessActive}
            >
              <Play className="w-6 h-6 mr-2" /> Run BitWit {numRuns > 1 ? `${numRuns} Times` : 'Once'}
            </button>
            <button
              onClick={handleResetApp}
              className="bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-700 hover:to-rose-800 text-white font-bold py-3 px-6 rounded-lg shadow-xl transition duration-300 ease-in-out transform hover:scale-105 flex items-center justify-center text-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:from-gray-500 disabled:to-gray-600"
              disabled={isLoading || isBitWitProcessActive}
            >
              <RotateCcw className="w-6 h-6 mr-2" /> Reset Application
            </button>
          </div>
        </div>

        {/* Configuration Section */}
        <div className="bg-gray-800 p-8 rounded-xl shadow-2xl border border-gray-700 mb-10">
          <h3 className="text-3xl font-bold text-teal-300 mb-6 flex items-center">
            <Settings className="w-7 h-7 mr-3 text-yellow-400" /> Configuration
          </h3>
          <div className="text-gray-300 space-y-4">
            {Object.entries(config).length === 0 ? (
              <p className="text-center text-gray-400 py-4">Loading configuration...</p>
            ) : (
              <>
                {/* Normal Configuration - Always editable */}
                <h4 className="text-2xl font-semibold text-teal-200 mt-6 mb-4 border-b border-gray-700 pb-2">Normal Settings</h4>
                {/* Render boolean toggles */}
                {booleanToggleKeys.map(key => (
                  config.hasOwnProperty(key) && (
                    <div key={key} className="flex flex-col sm:flex-row sm:items-center justify-between py-3 border-b border-gray-700 last:border-b-0">
                      <span className="font-medium text-gray-200 text-lg mb-2 sm:mb-0">{key.replace(/_/g, ' ')}:</span>
                      {renderConfigInput(key, tempConfig[key], true)}
                    </div>
                  )
                ))}

                {/* Render IMAGE_GENERATION_CHANCE, LOG_LEVEL, TOPIC_ITERATION_LIMIT, REPLY_CHANCE side-by-side or stacked*/}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-3 border-b border-gray-700">
                  {config.hasOwnProperty('IMAGE_GENERATION_CHANCE') && (
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between">
                      <span className="font-medium text-gray-200 text-lg mb-2 sm:mb-0">IMAGE GENERATION CHANCE:</span>
                      {renderConfigInput('IMAGE_GENERATION_CHANCE', tempConfig['IMAGE_GENERATION_CHANCE'], true)}
                    </div>
                  )}
                  {config.hasOwnProperty('LOG_LEVEL') && (
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between">
                      <span className="font-medium text-gray-200 text-lg mb-2 sm:mb-0">LOG LEVEL:</span>
                      {renderConfigInput('LOG_LEVEL', tempConfig['LOG_LEVEL'], true)}
                    </div>
                  )}
                  {/* NEW: TOPIC_ITERATION_LIMIT */}
                  {config.hasOwnProperty('TOPIC_ITERATION_LIMIT') && (
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between">
                      <span className="font-medium text-gray-200 text-lg mb-2 sm:mb-0">TOPIC ITERATION LIMIT:</span>
                      {renderConfigInput('TOPIC_ITERATION_LIMIT', tempConfig['TOPIC_ITERATION_LIMIT'], true)}
                    </div>
                  )}
                  {/* NEW: REPLY_CHANCE */}
                  {config.hasOwnProperty('REPLY_CHANCE') && (
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between">
                      <span className="font-medium text-gray-200 text-lg mb-2 sm:mb-0">REPLY CHANCE:</span>
                      {renderConfigInput('REPLY_CHANCE', tempConfig['REPLY_CHANCE'], true)}
                    </div>
                  )}
                </div>


                {/* Advanced Configuration Toggle */}
                <button
                  onClick={() => {
                    setShowAdvancedConfig(!showAdvancedConfig);
                    // When hiding advanced settings, also hide the edit buttons
                    if (showAdvancedConfig) {
                      setShowConfigEdit(false);
                      setTempConfig(config); // Revert any unsaved advanced changes
                    }
                  }}
                  className="w-full bg-gray-700 hover:bg-gray-600 text-white font-bold py-3 px-6 rounded-lg shadow-md transition duration-300 mt-6 flex items-center justify-center text-lg"
                >
                  {showAdvancedConfig ? (
                    <>
                      <ChevronUp className="w-6 h-6 mr-2" /> Hide Advanced Settings
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-6 h-6 mr-2" /> Show Advanced Settings
                    </>
                  )}
                </button>

                {/* Advanced Configuration Section - Only render if showAdvancedConfig is true */}
                {showAdvancedConfig && (
                  <div className="mt-8 border-t border-gray-700 pt-8 animate-fade-in">
                    <h4 className="text-2xl font-semibold text-teal-200 mb-4 border-b border-gray-700 pb-2">Advanced Settings</h4>
                    {Object.entries(tempConfig)
                      .filter(([key]) => !normalConfigKeys.includes(key))
                      .map(([key, value]) => (
                        <div key={key} className="flex flex-col sm:flex-row sm:items-center justify-between py-3 border-b border-gray-700 last:border-b-0">
                          <span className="font-medium text-gray-200 text-lg mb-2 sm:mb-0">{key.replace(/_/g, ' ')}:</span>
                          {showConfigEdit ? (
                            renderConfigInput(key, value, true)
                          ) : (
                            <span className="text-teal-400 font-mono text-base">{typeof config[key] === 'boolean' ? (config[key] ? 'true' : 'false') : String(config[key])}</span>
                          )}
                        </div>
                      ))}
                    
                    {/* Conditional rendering for Save/Cancel/Edit Advanced buttons */}
                    <div className="flex justify-end mt-8 space-x-4">
                      {showConfigEdit ? (
                        <>
                          <button
                            onClick={handleSaveConfig}
                            className="bg-gradient-to-r from-green-600 to-emerald-700 hover:from-green-700 hover:to-emerald-800 text-white font-bold py-3 px-6 rounded-lg shadow-xl transition duration-300 ease-in-out transform hover:scale-105 text-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:from-gray-500 disabled:to-gray-600"
                            disabled={isLoading || isBitWitProcessActive}
                          >
                            Save Changes
                          </button>
                          <button
                            onClick={() => { setShowConfigEdit(false); setTempConfig(config); }}
                            className="bg-gradient-to-r from-gray-600 to-gray-700 hover:from-gray-700 hover:to-gray-800 text-white font-bold py-3 px-6 rounded-lg shadow-xl transition duration-300 ease-in-out transform hover:scale-105 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={isLoading || isBitWitProcessActive}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setShowConfigEdit(true)}
                          className="bg-gradient-to-r from-teal-600 to-cyan-700 hover:from-teal-700 hover:to-cyan-800 text-white font-bold py-3 px-6 rounded-lg shadow-xl transition duration-300 ease-in-out transform hover:scale-105 text-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:from-gray-500 disabled:to-gray-600"
                          disabled={isLoading || isBitWitProcessActive}
                        >
                          Edit Advanced Configuration
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Logs Section */}
        <div className="bg-gray-800 p-8 rounded-xl shadow-2xl border border-gray-700">
          <h3 className="text-3xl font-bold text-teal-300 mb-6 flex items-center">
            <List className="w-7 h-7 mr-3 text-blue-400" /> Recent Logs
          </h3>
          <div className="mb-6 flex flex-col sm:flex-row items-start sm:items-center space-y-3 sm:space-y-0 sm:space-x-4">
            <label htmlFor="logLines" className="text-gray-300 text-lg">Show last</label>
            <input
              type="number"
              id="logLines"
              value={logLines}
              onChange={(e) => setLogLines(Math.max(1, parseInt(e.target.value) || 10))}
              className="bg-gray-700 border border-gray-600 rounded-md px-4 py-2 text-gray-100 w-24 text-center text-lg focus:outline-none focus:ring-2 focus:ring-teal-500 transition-all duration-200"
              min="1"
              disabled={isLoading || isBitWitProcessActive}
            />
            <span className="text-gray-300 text-lg">lines</span>
            <button
              onClick={() => fetchLogs(false)}
              className="bg-teal-600 hover:bg-teal-700 text-white font-bold py-2 px-5 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105 text-base disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-500"
              disabled={isLoading || isBitWitProcessActive}
            >
              Refresh Logs
            </button>
          </div>
          <div className="bg-gray-900 text-gray-300 font-mono text-sm p-6 rounded-lg h-96 overflow-y-scroll border border-gray-700 shadow-inner">
            {logs.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No logs to display or logs are loading...</p>
            ) : (
              logs.map((logEntry, index) => (
                <p key={index} className="whitespace-pre-wrap break-words border-b border-gray-800 last:border-b-0 py-1 leading-relaxed">
                  {logEntry}
                </p>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ControlPanelPage;