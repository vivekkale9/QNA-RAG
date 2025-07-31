import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useAuth } from '@/contexts/AuthContext';
import { Settings, Database, BarChart3, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [backupStats, setBackupStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Rebuild progress state
  const [rebuildProgress, setRebuildProgress] = useState({
    isActive: false,
    status: '',
    progress: 0,
    message: '',
    totalChunks: 0,
    processedChunks: 0,
    totalDocuments: 0,
    processedDocuments: 0,
  });

  // Only allow admin users to access this page
  if (!user || user.role !== 'admin') {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto text-center space-y-4">
          <AlertTriangle className="w-16 h-16 text-destructive mx-auto" />
          <h1 className="text-2xl font-bold">Access Denied</h1>
          <p className="text-muted-foreground">
            This page is only accessible to administrators.
          </p>
        </div>
      </div>
    );
  }

  const fetchBackupStats = async () => {
    try {
      const response = await apiClient.getBackupStats();
      setBackupStats(response.data);
    } catch (error: any) {
      toast({
        title: "Error",
        description: "Failed to fetch backup statistics",
        variant: "destructive",
      });
    }
  };

  const rebuildVectorStore = async () => {
    try {
      setIsLoading(true);
      setRebuildProgress({
        isActive: true,
        status: 'starting',
        progress: 0,
        message: 'Initializing rebuild...',
        totalChunks: 0,
        processedChunks: 0,
        totalDocuments: 0,
        processedDocuments: 0,
      });

      const result = await apiClient.rebuildVectorStoreWithProgress(
        undefined, // No filters for now
        (data) => {
          // Update progress in real-time
          setRebuildProgress(prev => ({
            ...prev,
            status: data.status,
            progress: data.progress,
            message: data.message,
            totalChunks: data.total_chunks,
            processedChunks: data.processed_chunks,
            totalDocuments: data.total_documents,
            processedDocuments: data.processed_documents,
          }));
        }
      );

      if (result.success) {
        setRebuildProgress(prev => ({
          ...prev,
          isActive: false,
          status: 'completed',
          progress: 100,
        }));
        
        toast({
          title: "Rebuild Completed",
          description: "Vector store rebuild completed successfully!",
        });
        
        // Refresh backup stats after successful rebuild
        await fetchBackupStats();
      } else {
        throw new Error(result.data?.error || 'Rebuild failed');
      }
    } catch (error: any) {
      setRebuildProgress(prev => ({
        ...prev,
        isActive: false,
        status: 'failed',
      }));
      
      toast({
        title: "Error",
        description: error.message || "Failed to rebuild vector store",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBackupStats();
  }, []);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold text-gradient">Admin Settings</h1>
          <p className="text-muted-foreground">
            Vector Store Management & System Administration
          </p>
          <Badge variant="secondary" className="bg-primary/10 text-primary">
            Administrator Access
          </Badge>
        </div>

        <div className="grid gap-6">
          {/* Backup Statistics */}
          <Card className="glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-primary" />
                Backup Statistics
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <h4 className="text-sm font-medium">MongoDB Backup Data</h4>
                  <p className="text-xs text-muted-foreground">
                    View statistics about available backup data for rebuild operations
                  </p>
                </div>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={fetchBackupStats}
                >
                  <BarChart3 className="mr-2 h-3 w-3" />
                  Refresh Stats
                </Button>
              </div>

              {backupStats && (
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div className="p-3 bg-muted/30 rounded-lg">
                    <div className="text-xs text-muted-foreground">Total Documents</div>
                    <div className="font-medium">{backupStats.total_documents || 0}</div>
                  </div>
                  <div className="p-3 bg-muted/30 rounded-lg">
                    <div className="text-xs text-muted-foreground">Total Chunks</div>
                    <div className="font-medium">{backupStats.total_chunks || 0}</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Vector Store Management */}
          <Card className="glass">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="w-5 h-5 text-primary" />
                Vector Store Management
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <div className="p-4 bg-muted/30 rounded-lg space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <h4 className="text-sm font-medium">Rebuild Vector Store</h4>
                      <p className="text-xs text-muted-foreground">
                        Rebuild the entire vector store from MongoDB backup (disaster recovery)
                      </p>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={rebuildVectorStore}
                      disabled={isLoading || rebuildProgress.isActive}
                    >
                      <Database className="mr-2 h-3 w-3" />
                      {rebuildProgress.isActive ? 'Rebuilding...' : 'Rebuild Store'}
                    </Button>
                  </div>

                  {/* Progress UI */}
                  {(rebuildProgress.isActive || rebuildProgress.status === 'completed' || rebuildProgress.status === 'failed') && (
                    <div className="space-y-3 pt-4 border-t border-border/50">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {rebuildProgress.status === 'completed' && (
                            <CheckCircle className="w-4 h-4 text-green-600" />
                          )}
                          {rebuildProgress.status === 'failed' && (
                            <XCircle className="w-4 h-4 text-red-600" />
                          )}
                          {rebuildProgress.isActive && (
                            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                          )}
                          <span className="text-sm font-medium">
                            {rebuildProgress.status === 'completed' ? 'Rebuild Complete' : 
                             rebuildProgress.status === 'failed' ? 'Rebuild Failed' : 
                             'Rebuilding Vector Store'}
                          </span>
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {Math.round(rebuildProgress.progress)}%
                        </span>
                      </div>
                      
                      <Progress value={rebuildProgress.progress} className="w-full" />
                      
                      <div className="text-xs text-muted-foreground">
                        {rebuildProgress.message}
                      </div>
                      
                      {rebuildProgress.totalChunks > 0 && (
                        <div className="grid grid-cols-2 gap-4 text-xs">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Chunks:</span>
                            <span>{rebuildProgress.processedChunks}/{rebuildProgress.totalChunks}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Documents:</span>
                            <span>{rebuildProgress.processedDocuments}/{rebuildProgress.totalDocuments}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
                    <div className="text-xs text-amber-800">
                      <strong>Warning:</strong> Rebuild operations may take significant time for large datasets. 
                      The progress bar will show real-time updates. Only use this for disaster recovery or data migration scenarios.
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}; 