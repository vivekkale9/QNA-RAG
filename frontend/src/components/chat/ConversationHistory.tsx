import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/lib/api';
import { Conversation } from '@/types/api';
import { MessageSquare, Plus, Clock, Trash2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface ConversationHistoryProps {
  selectedConversationId?: string;
  onConversationSelect: (conversationId: string) => void;
  onNewConversation: () => void;
  refreshTrigger?: number;
}

export const ConversationHistory: React.FC<ConversationHistoryProps> = ({
  selectedConversationId,
  onConversationSelect,
  onNewConversation,
  refreshTrigger,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  const loadConversations = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.getConversations();
      setConversations(response.data || []);
    } catch (error: any) {
      console.error('Failed to load conversations:', error);
      toast({
        title: "Failed to load conversations",
        description: error.response?.data?.detail || "An error occurred while loading conversations.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  // Refresh conversations when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger) {
      loadConversations();
    }
  }, [refreshTrigger]);

  const truncateTitle = (title: string, maxLength: number = 30) => {
    if (title.length <= maxLength) return title;
    return `${title.substring(0, maxLength)}...`;
  };

  return (
    <Card className="glass h-[calc(100vh-12rem)] flex flex-col">
      <CardHeader className="flex-shrink-0 pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <MessageSquare className="w-5 h-5 text-primary" />
            Conversations
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onNewConversation}
            className="flex items-center gap-2 hover:bg-primary/10"
          >
            <Plus className="w-4 h-4" />
            New
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea className="h-full px-4 pb-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8 space-y-3">
              <div className="w-12 h-12 bg-muted rounded-xl flex items-center justify-center mx-auto">
                <MessageSquare className="w-6 h-6 text-muted-foreground" />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium">No conversations yet</p>
                <p className="text-xs text-muted-foreground">
                  Start a new conversation to begin
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className={`p-3 rounded-lg cursor-pointer transition-all hover:bg-primary/5 ${
                    selectedConversationId === conversation.id
                      ? 'bg-primary/10 border border-primary/20'
                      : 'bg-muted/30 hover:bg-muted/50'
                  }`}
                  onClick={() => onConversationSelect(conversation.id)}
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between">
                      <h4 className="text-sm font-medium leading-tight">
                        {truncateTitle(conversation.title)}
                      </h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 hover:bg-destructive/10 hover:text-destructive"
                        onClick={(e) => {
                          e.stopPropagation();
                          // TODO: Implement delete conversation
                        }}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                    
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>
                          {formatDistanceToNow(new Date(conversation.updated_at), { 
                            addSuffix: true 
                          })}
                        </span>
                      </div>
                      <span className="text-xs bg-muted/50 px-1.5 py-0.5 rounded">
                        {Math.floor(conversation.message_count / 2)} message{Math.floor(conversation.message_count / 2) !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}; 