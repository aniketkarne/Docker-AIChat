// @ts-nocheck
import { useState } from 'react'
import axios from 'axios'
import dynamic from 'next/dynamic'
import { Bar } from 'react-chartjs-2'
import 'chart.js/auto'

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false })

export default function Home() {
  const [rawDockerfile, setRawDockerfile] = useState('')
  const [optimized, setOptimized] = useState('')
  const [lintResults, setLintResults] = useState<string[]>([])
  const [layerReport, setLayerReport] = useState<number[]>([])
  const [sessionID, setSessionID] = useState<string>('')
  const [chatOpen, setChatOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([])
  const [chatInput, setChatInput] = useState('')

  const handleOptimize = async () => {
    const formData = new FormData()
    formData.append('file', new Blob([rawDockerfile], { type: 'text/plain' }), 'Dockerfile')
    const uploadResp = await axios.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    const sid = uploadResp.data.sessionID
    setSessionID(sid)
    const optimizeResp = await axios.post('/optimize', {
      dockerfile: rawDockerfile,
      sessionID: sid
    })
    setOptimized(optimizeResp.data.optimizedDockerfile)
    setLintResults(optimizeResp.data.lintResults)
    setLayerReport(optimizeResp.data.layerReport)
  }

  const handleDownload = () => {
    const blob = new Blob([optimized], { type: 'text/plain' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'Dockerfile.optimized'
    link.click()
  }

  const sendChat = async () => {
    const payload = { sessionID, history: chatHistory, question: chatInput }
    const resp = await axios.post('/chat', payload)
    setChatHistory(resp.data.history)
    setChatInput('')
  }

  return (
    <div className="relative bg-netflix-background text-netflix-text min-h-screen overflow-hidden">
      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-black to-transparent opacity-60 pointer-events-none" />
      <div className="relative z-10">
        <nav className="bg-netflix-card fixed w-full z-20 top-0">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center">
            <span className="text-2xl font-bold text-netflix-primary">DOCKERFLIX</span>
          </div>
        </nav>
        <div className="pt-24 pb-10">
          <div className="max-w-3xl mx-auto px-6">
            <h1 className="text-4xl font-bold mb-6 text-netflix-primary">Optimize Your Dockerfile</h1>
            {!optimized ? (
              <div className="space-y-6">
                <textarea
                  rows={10}
                  className="w-full p-4 bg-netflix-card rounded-md focus:outline-none focus:ring-2 focus:ring-netflix-accent"
                  placeholder="Paste your Dockerfile here..."
                  value={rawDockerfile}
                  onChange={(e) => setRawDockerfile(e.target.value)}
                />
                <button
                  className="w-full py-3 bg-netflix-primary text-netflix-text font-semibold rounded-md hover:bg-netflix-accent transition"
                  onClick={handleOptimize}
                  disabled={!rawDockerfile}
                >
                  Optimize
                </button>
              </div>
            ) : (
              <>
                <div className="mb-6">
                  <MonacoEditor
                    height="50vh"
                    defaultLanguage="dockerfile"
                    value={optimized}
                    options={{ minimap: { enabled: false }, theme: 'vs-dark' }}
                  />
                  <div className="mt-4 flex space-x-4">
                    <button
                      className="px-4 py-2 bg-green-600 rounded-md hover:bg-green-700 transition"
                      onClick={handleDownload}
                    >
                      Download
                    </button>
                    <button
                      className="px-4 py-2 bg-netflix-primary rounded-md hover:bg-netflix-accent transition"
                      onClick={() => setChatOpen(!chatOpen)}
                    >
                      {chatOpen ? 'Close Chat' : 'Chat'}
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="p-4 bg-netflix-card rounded-md">
                    <h2 className="font-semibold mb-2 text-netflix-primary">Lint Results</h2>
                    {lintResults.length > 0 ? (
                      <ul className="list-disc list-inside space-y-1 text-netflix-text">
                        {lintResults.map((l, i) => (
                          <li key={i}>{l}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-netflix-text opacity-60">No lint issues.</p>
                    )}
                  </div>
                  <div className="p-4 bg-netflix-card rounded-md">
                    <h2 className="font-semibold mb-2 text-netflix-primary">Layer Sizes</h2>
                    <Bar
                      data={{
                        labels: layerReport.map((_, i) => `Layer ${i + 1}`),
                        datasets: [
                          {
                            label: 'Size (bytes)',
                            data: layerReport,
                            backgroundColor: 'rgba(220,38,38,0.7)',
                          },
                        ],
                      }}
                    />
                  </div>
                </div>
                {chatOpen && (
                  <div className="mt-6 p-4 bg-netflix-card rounded-md">
                    <h2 className="font-semibold mb-2 text-netflix-primary">Chat with AI</h2>
                    <div className="max-h-48 overflow-y-auto mb-4 space-y-2">
                      {chatHistory.map((msg, i) => (
                        <div
                          key={i}
                          className={msg.role === 'assistant' ? 'text-green-400' : 'text-netflix-text'}
                        >
                          <strong>{msg.role === 'assistant' ? 'AI' : 'You'}:</strong> {msg.content}
                        </div>
                      ))}
                    </div>
                    <div className="flex">
                      <input
                        className="flex-grow p-2 bg-netflix-background rounded-l-md focus:outline-none focus:ring-2 focus:ring-netflix-accent"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        placeholder="Ask a question..."
                      />
                      <button
                        className="px-4 py-2 bg-netflix-primary rounded-r-md hover:bg-netflix-accent transition"
                        onClick={sendChat}
                      >
                        Send
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
