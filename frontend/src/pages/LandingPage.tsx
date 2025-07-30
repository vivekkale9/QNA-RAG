import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MessageSquare, Shield, Zap, Brain, ArrowRight } from 'lucide-react';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-subtle">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-primary rounded-xl flex items-center justify-center shadow-glow">
              <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gradient">DocuChat AI</h1>
          </div>

          <div className="flex items-center space-x-4">
            <Button 
              variant="ghost" 
              onClick={() => navigate('/auth/login')}
            >
              Sign In
            </Button>
            <Button 
              variant="gradient"
              onClick={() => navigate('/auth/register')}
            >
              Get Started
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 py-16 space-y-20">
        <div className="text-center space-y-8 max-w-4xl mx-auto">
          <div className="space-y-6">
            <h1 className="text-5xl md:text-6xl font-bold leading-tight">
              <span className="text-gradient">Intelligent Document</span><br />
              Analysis with AI
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
              Upload your documents and unlock powerful insights with our advanced RAG-powered 
              question answering system. Get instant, accurate answers from your document content.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              variant="gradient" 
              size="xl"
              onClick={() => navigate('/auth/register')}
              className="flex items-center gap-2"
            >
              Start Free Trial
              <ArrowRight className="w-5 h-5" />
            </Button>
            <Button 
              variant="outline" 
              size="xl"
              onClick={() => navigate('/auth/login')}
              className="flex items-center gap-2"
            >
              <MessageSquare className="w-5 h-5" />
              See Demo
            </Button>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          <Card className="glass hover:shadow-glow transition-all group">
            <CardContent className="p-8 text-center space-y-4">
              <div className="w-16 h-16 bg-primary/20 rounded-2xl flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                <Brain className="w-8 h-8 text-primary" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Smart Analysis</h3>
                <p className="text-sm text-muted-foreground">
                  Advanced AI models understand context and meaning in your documents.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="glass hover:shadow-glow transition-all group">
            <CardContent className="p-8 text-center space-y-4">
              <div className="w-16 h-16 bg-success/20 rounded-2xl flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                <Zap className="w-8 h-8 text-success" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Lightning Fast</h3>
                <p className="text-sm text-muted-foreground">
                  Get instant answers with optimized vector search technology.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="glass hover:shadow-glow transition-all group">
            <CardContent className="p-8 text-center space-y-4">
              <div className="w-16 h-16 bg-warning/20 rounded-2xl flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                <Shield className="w-8 h-8 text-warning" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Secure & Private</h3>
                <p className="text-sm text-muted-foreground">
                  Enterprise-grade security keeps your documents safe and private.
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="glass hover:shadow-glow transition-all group">
            <CardContent className="p-8 text-center space-y-4">
              <div className="w-16 h-16 bg-primary/20 rounded-2xl flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                <MessageSquare className="w-8 h-8 text-primary" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Natural Conversations</h3>
                <p className="text-sm text-muted-foreground">
                  Ask questions in natural language and get human-like responses.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* CTA Section */}
        <div className="text-center space-y-8">
          <Card className="glass max-w-2xl mx-auto">
            <CardContent className="p-12 space-y-6">
              <div className="space-y-4">
                <h2 className="text-3xl font-bold text-gradient">Ready to get started?</h2>
                <p className="text-muted-foreground">
                  Join thousands of users who are already using DocuChat AI to unlock insights from their documents.
                </p>
              </div>
              <Button 
                variant="gradient" 
                size="lg"
                onClick={() => navigate('/auth/register')}
                className="w-full sm:w-auto"
              >
                Create Free Account
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 mt-20">
        <div className="text-center text-sm text-muted-foreground">
          <p>© 2024 DocuChat AI. Built with cutting-edge RAG technology.</p>
        </div>
      </footer>
    </div>
  );
};