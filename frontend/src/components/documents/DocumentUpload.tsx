import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/lib/api';
import { Upload, FileText, AlertCircle, CheckCircle2, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface UploadFile {
  file: File;
  id: string;
  progress: number;
  status: 'uploading' | 'success' | 'error';
  stage?: string;
  error?: string;
}

interface DocumentUploadProps {
  onUploadComplete?: () => void;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({ onUploadComplete }) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadFile[]>([]);
  const { toast } = useToast();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      progress: 0,
      status: 'uploading',
    }));

    setUploadedFiles(prev => [...prev, ...newFiles]);

    // Upload each file
    newFiles.forEach(uploadFile => {
      uploadDocument(uploadFile);
    });
  }, []);

  const uploadDocument = async (uploadFile: UploadFile) => {
    try {
      await apiClient.uploadDocument(
        uploadFile.file,
        (stage: string, progress?: number) => {
          setUploadedFiles(prev =>
            prev.map(f =>
              f.id === uploadFile.id
                ? { 
                    ...f, 
                    stage,
                    progress: progress || f.progress,
                    status: stage === 'processed' ? 'success' : 'uploading'
                  }
                : f
            )
          );

          // Show completion toast when processing is done
          if (stage === 'processed') {
            toast({
              title: "Upload successful",
              description: `${uploadFile.file.name} has been processed and is ready for use.`,
            });
            onUploadComplete?.();
          }
        }
      );
      
      // Ensure status is set to success if upload completes without explicit 'processed' stage
      setUploadedFiles(prev =>
        prev.map(f =>
          f.id === uploadFile.id && f.status === 'uploading'
            ? { ...f, status: 'success', progress: 100, stage: 'completed' }
            : f
        )
      );
    } catch (error: any) {
      const errorMessage = error.message || 'Upload failed';
      
      setUploadedFiles(prev =>
        prev.map(f =>
          f.id === uploadFile.id
            ? { ...f, status: 'error', error: errorMessage, stage: 'failed' }
            : f
        )
      );

      toast({
        title: "Upload failed",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const removeFile = (id: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== id));
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: true,
  });

  return (
    <div className="space-y-6">
      <Card className="glass border-dashed border-2 border-border/50 hover:border-primary/50 transition-colors">
        <CardContent className="p-8">
          <div
            {...getRootProps()}
            className={cn(
              "cursor-pointer text-center space-y-4 transition-all",
              isDragActive && "scale-105"
            )}
          >
            <input {...getInputProps()} />
            <div className="flex justify-center">
              <div className={cn(
                "w-16 h-16 rounded-2xl flex items-center justify-center transition-all",
                isDragActive 
                  ? "bg-primary shadow-glow scale-110" 
                  : "bg-muted hover:bg-primary/20"
              )}>
                <Upload className={cn(
                  "w-8 h-8 transition-colors",
                  isDragActive ? "text-white" : "text-muted-foreground"
                )} />
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold">
                {isDragActive ? "Drop files here" : "Upload your documents"}
              </h3>
              <p className="text-sm text-muted-foreground">
                Drag and drop PDF, TXT, or MD files here, or click to browse
              </p>
              <p className="text-xs text-muted-foreground">
                Maximum file size: 50MB • Supported formats: PDF, TXT, MD
              </p>
            </div>

            <Button variant="outline" className="mt-4">
              Browse Files
            </Button>
          </div>
        </CardContent>
      </Card>

      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-muted-foreground">Upload Progress</h4>
          {uploadedFiles.map((uploadFile) => (
            <Card key={uploadFile.id} className="glass">
              <CardContent className="p-4">
                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0">
                    <FileText className="w-8 h-8 text-primary" />
                  </div>

                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium truncate">
                        {uploadFile.file.name}
                      </p>
                      <div className="flex items-center space-x-2">
                        {uploadFile.status === 'uploading' && (
                          <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                        )}
                        {uploadFile.status === 'success' && (
                          <CheckCircle2 className="w-4 h-4 text-success" />
                        )}
                        {uploadFile.status === 'error' && (
                          <AlertCircle className="w-4 h-4 text-destructive" />
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFile(uploadFile.id)}
                          className="h-6 w-6 p-0"
                        >
                          <X className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>

                    {uploadFile.status === 'uploading' && (
                      <Progress value={uploadFile.progress} className="h-2" />
                    )}

                    {uploadFile.status === 'error' && uploadFile.error && (
                      <p className="text-xs text-destructive">{uploadFile.error}</p>
                    )}

                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{(uploadFile.file.size / 1024 / 1024).toFixed(2)} MB</span>
                      <span className="capitalize">
                        {uploadFile.stage || uploadFile.status}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};