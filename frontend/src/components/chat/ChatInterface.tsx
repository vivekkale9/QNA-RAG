import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/lib/api';
import { Message, DocumentSource } from '@/types/api';
import { Send, Bot, User, FileText, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface ChatInterfaceProps {
  conversationId?: string;
  onConversationCreated?: (conversationId: string) => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ conversationId, onConversationCreated }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [input, setInput] = useState('');
  const [sources, setSources] = useState<DocumentSource[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load conversation history when conversationId changes
  useEffect(() => {
    const loadConversationHistory = async () => {
      if (conversationId) {
        try {
          const response = await apiClient.getConversation(conversationId);
          const conversation = response.data;
          if (conversation.messages) {
            setMessages(conversation.messages);
            // Set sources from the last assistant message if any
            const lastAssistantMessage = conversation.messages
              .filter(msg => msg.role === 'assistant')
              .pop();
            if (lastAssistantMessage?.sources) {
              setSources(lastAssistantMessage.sources);
            } else {
              setSources([]);
            }
          }
        } catch (error) {
          console.error('Failed to load conversation history:', error);
        }
      } else {
        // Clear messages and sources when starting a new conversation
        setMessages([]);
        setSources([]);
      }
    };

    loadConversationHistory();
  }, [conversationId]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    // Clear previous sources when sending new message
    setSources([]);

    try {
      const response = await apiClient.sendMessage({
        message: input.trim(),
        conversation_id: conversationId,
        max_chunks: 5,
      });

      const assistantMessage: Message = {
        id: parseInt(response.data.message_id),
        role: 'assistant',
        content: response.data.message,
        sources: response.data.sources,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => prev.map(msg => 
        msg.id === userMessage.id 
          ? { ...userMessage, id: Date.now() + 1 }
          : msg
      ).concat(assistantMessage));

      // Set sources only for current response
      setSources(response.data.sources || []);
      
      // If this is a new conversation (no conversationId prop but response has one), notify parent
      if (!conversationId && response.data.conversation_id && onConversationCreated) {
        onConversationCreated(response.data.conversation_id);
      }
    } catch (error: any) {
      toast({
        title: "Failed to send message",
        description: error.response?.data?.detail || "An error occurred while sending your message.",
        variant: "destructive",
      });

      // Remove the temporary user message on error
      setMessages(prev => prev.filter(msg => msg.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-12rem)]">
      {/* Chat Messages */}
      <div className="lg:col-span-1 flex flex-col">
        <Card className="glass flex-1 flex flex-col max-h-[calc(100vh-12rem)]">
          <CardHeader className="border-b border-border/50 flex-shrink-0">
            <CardTitle className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-primary" />
              AI Assistant
            </CardTitle>
          </CardHeader>

          <CardContent className="flex-1 p-0 overflow-hidden">
            <ScrollArea className="h-[calc(100vh-20rem)] p-6">
              <div className="space-y-6">
                {messages.length === 0 && (
                  <div className="text-center space-y-4 py-12">
                    <div className="w-16 h-16 bg-primary/20 rounded-2xl flex items-center justify-center mx-auto">
                      <Bot className="w-8 h-8 text-primary" />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-lg font-semibold">Start a conversation</h3>
                      <p className="text-sm text-muted-foreground max-w-md mx-auto">
                        Ask questions about your uploaded documents and get intelligent answers powered by AI.
                      </p>
                    </div>
                  </div>
                )}

                {messages.map((message) => (
                  <div key={message.id} className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                        message.role === 'user' 
                          ? 'bg-muted' 
                          : 'bg-primary/20'
                      }`}>
                        {message.role === 'user' ? (
                          <User className="w-4 h-4" />
                        ) : (
                          <Bot className="w-4 h-4 text-primary" />
                        )}
                      </div>

                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">
                            {message.role === 'user' ? 'You' : 'AI Assistant'}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
                          </span>
                        </div>

                        <div className={`prose prose-sm max-w-none ${
                          message.role === 'user' 
                            ? 'bg-muted/50 p-4 rounded-xl' 
                            : 'bg-primary/5 p-4 rounded-xl'
                        }`}>
                          <p className="whitespace-pre-wrap m-0">{message.content}</p>
                        </div>

                        {message.sources && message.sources.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-xs text-muted-foreground font-medium">
                              Sources ({message.sources.length}):
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {message.sources.map((source, index) => (
                                <Badge 
                                  key={source.chunk_id} 
                                  variant="outline"
                                  className="text-xs"
                                >
                                  {source.document_name} (Score: {source.similarity_score.toFixed(2)})
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 bg-primary/20 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">AI Assistant</span>
                        <span className="text-xs text-muted-foreground">typing...</span>
                      </div>
                      <div className="bg-primary/5 p-4 rounded-xl flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-primary" />
                        <span className="text-sm text-muted-foreground">
                          Analyzing documents and generating response...
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>
          </CardContent>

          {/* Input Area */}
          <div className="p-4 border-t border-border/50">
            <div className="flex gap-3">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question about your documents..."
                className="glass flex-1"
                disabled={isLoading}
              />
              <Button 
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
                variant="gradient"
                size="icon"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Sources Panel */}
      <div className="space-y-6">
        <Card className="glass h-[calc(100vh-12rem)] flex flex-col">
          <CardHeader className="flex-shrink-0">
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              Document Sources
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-hidden p-0">
            <ScrollArea className="h-full p-6">
            {sources.length === 0 ? (
              <div className="text-center space-y-3 py-8">
                <div className="w-12 h-12 bg-muted rounded-xl flex items-center justify-center mx-auto">
                  <FileText className="w-6 h-6 text-muted-foreground" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium">
                    {messages.length > 0 && messages[messages.length - 1]?.role === 'assistant' 
                      ? "No relevant documents found" 
                      : "No sources yet"
                    }
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {messages.length > 0 && messages[messages.length - 1]?.role === 'assistant'
                      ? "The AI couldn't find relevant information in your uploaded documents for the last question"
                      : "Send a message to see relevant document excerpts"
                    }
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {sources.map((source, index) => (
                  <div key={source.chunk_id} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="text-xs">
                        {source.document_name}
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {(source.similarity_score * 100).toFixed(1)}% match
                      </Badge>
                    </div>
                    
                    <div className="bg-muted/50 p-3 rounded-lg">
                      <p className="text-xs leading-relaxed">
                        {source.content.length > 200 
                          ? `${source.content.substring(0, 200)}...` 
                          : source.content
                        }
                      </p>
                    </div>

                    {index < sources.length - 1 && <Separator />}
                  </div>
                ))}
              </div>
            )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};