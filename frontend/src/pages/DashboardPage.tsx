import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DocumentUpload } from '@/components/documents/DocumentUpload';
import { DocumentList } from '@/components/documents/DocumentList';
import { useNavigate } from 'react-router-dom';
import { MessageSquare, FileText, Upload, Brain, Zap, Shield } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const navigate = useNavigate();

  const handleUploadComplete = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-6">
        <div className="space-y-4">
          <h1 className="text-4xl font-bold text-gradient">
            AI-Powered Document Analysis
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Upload your documents and unlock intelligent insights with our advanced RAG-powered question answering system.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button 
            variant="gradient" 
            size="lg"
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2"
          >
            <MessageSquare className="w-5 h-5" />
            Start Chatting
          </Button>
          <Button 
            variant="outline" 
            size="lg"
            className="flex items-center gap-2"
          >
            <Upload className="w-5 h-5" />
            Upload Documents
          </Button>
        </div>
      </div>

      {/* Features */}
      <div className="grid md:grid-cols-3 gap-6">
        <Card className="glass hover:shadow-glow transition-all">
          <CardContent className="p-6 text-center space-y-4">
            <div className="w-12 h-12 bg-primary/20 rounded-xl flex items-center justify-center mx-auto">
              <Brain className="w-6 h-6 text-primary" />
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">Intelligent Analysis</h3>
              <p className="text-sm text-muted-foreground">
                Advanced AI models analyze your documents for deep understanding and context.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="glass hover:shadow-glow transition-all">
          <CardContent className="p-6 text-center space-y-4">
            <div className="w-12 h-12 bg-success/20 rounded-xl flex items-center justify-center mx-auto">
              <Zap className="w-6 h-6 text-success" />
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">Lightning Fast</h3>
              <p className="text-sm text-muted-foreground">
                Get instant answers to your questions with optimized vector search technology.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="glass hover:shadow-glow transition-all">
          <CardContent className="p-6 text-center space-y-4">
            <div className="w-12 h-12 bg-warning/20 rounded-xl flex items-center justify-center mx-auto">
              <Shield className="w-6 h-6 text-warning" />
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold">Secure & Private</h3>
              <p className="text-sm text-muted-foreground">
                Your documents are processed with enterprise-grade security and privacy.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="upload" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2 glass">
          <TabsTrigger value="upload" className="flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Upload Documents
          </TabsTrigger>
          <TabsTrigger value="documents" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            My Documents
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-6">
          <Card className="glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5 text-primary" />
                Upload New Documents
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DocumentUpload onUploadComplete={handleUploadComplete} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="documents" className="space-y-6">
          <DocumentList refreshTrigger={refreshTrigger} />
        </TabsContent>
      </Tabs>
    </div>
  );
};