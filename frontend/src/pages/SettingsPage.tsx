import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { Settings, Database, BarChart3, AlertTriangle } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

export const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [backupStats, setBackupStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

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
      const response = await apiClient.rebuildVectorStore();
      toast({
        title: "Rebuild Started",
        description: "Vector store rebuild has been initiated. This may take some time.",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to start rebuild",
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
                <div className="flex items-center justify-between p-4 bg-muted/30 rounded-lg">
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
                    disabled={isLoading}
                  >
                    <Database className="mr-2 h-3 w-3" />
                    Rebuild Store
                  </Button>
                </div>

                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
                    <div className="text-xs text-amber-800">
                      <strong>Warning:</strong> Rebuild operations may take significant time for large datasets. 
                      Only use this for disaster recovery or data migration scenarios.
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