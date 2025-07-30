import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/lib/api';
import { Document } from '@/types/api';
import { FileText, Trash2, Clock, CheckCircle2, AlertCircle, Download } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface DocumentListProps {
  refreshTrigger?: number;
}

export const DocumentList: React.FC<DocumentListProps> = ({ refreshTrigger }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());
  const { toast } = useToast();

  const fetchDocuments = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.getDocuments();
      setDocuments(response.data);
    } catch (error: any) {
      toast({
        title: "Failed to load documents",
        description: error.response?.data?.detail || "An error occurred while loading documents.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [refreshTrigger]);

  const handleDelete = async (documentId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeletingIds(prev => new Set(prev).add(documentId));
      await apiClient.deleteDocument(documentId);
      setDocuments(prev => prev.filter(doc => doc.id !== documentId));
      
      toast({
        title: "Document deleted",
        description: `${filename} has been successfully deleted.`,
      });
    } catch (error: any) {
      toast({
        title: "Failed to delete document",
        description: error.response?.data?.detail || "An error occurred while deleting the document.",
        variant: "destructive",
      });
    } finally {
      setDeletingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(documentId);
        return newSet;
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-success" />;
      case 'processing':
        return <Clock className="w-4 h-4 text-warning" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-destructive" />;
      default:
        return <Clock className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'failed':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  if (isLoading) {
    return (
      <Card className="glass">
        <CardContent className="p-8 text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading documents...</p>
        </CardContent>
      </Card>
    );
  }

  if (documents.length === 0) {
    return (
      <Card className="glass">
        <CardContent className="p-8 text-center space-y-4">
          <div className="w-16 h-16 bg-muted rounded-2xl flex items-center justify-center mx-auto">
            <FileText className="w-8 h-8 text-muted-foreground" />
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">No documents yet</h3>
            <p className="text-sm text-muted-foreground">
              Upload your first document to start analyzing with AI
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Your Documents</h3>
        <Badge variant="outline" className="glass">
          {documents.length} document{documents.length !== 1 ? 's' : ''}
        </Badge>
      </div>

      <div className="grid gap-4">
        {documents.map((document) => (
          <Card key={document.id} className="glass hover:shadow-glow transition-all">
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-primary/20 rounded-xl flex items-center justify-center">
                      <FileText className="w-5 h-5 text-primary" />
                    </div>
                  </div>

                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-medium truncate">
                        {document.name}
                      </h4>
                      <div className="flex items-center space-x-1">
                        {getStatusIcon(document.status)}
                        <Badge 
                          variant={getStatusColor(document.status) as any}
                          className="text-xs"
                        >
                          {document.status}
                        </Badge>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                      <span>{document.file_type.toUpperCase()}</span>
                      <span>{(document.file_size / 1024 / 1024).toFixed(2)} MB</span>
                      {document.chunk_count > 0 && (
                        <span>{document.chunk_count} chunks</span>
                      )}
                      <span>
                        {formatDistanceToNow(new Date(document.uploaded_at), { addSuffix: true })}
                      </span>
                    </div>

                    {document.status === 'processing' && (
                      <div className="flex items-center space-x-2 text-xs text-warning">
                        <div className="w-3 h-3 border border-warning border-t-transparent rounded-full animate-spin" />
                        <span>Processing document for AI analysis...</span>
                      </div>
                    )}

                    {document.status === 'failed' && (
                      <p className="text-xs text-destructive">
                        Processing failed. Please try uploading again.
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(document.id, document.name)}
                    disabled={deletingIds.has(document.id)}
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};