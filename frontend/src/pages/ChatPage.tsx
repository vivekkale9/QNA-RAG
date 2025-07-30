import React, { useState } from 'react';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ConversationHistory } from '@/components/chat/ConversationHistory';

export const ChatPage: React.FC = () => {
  const [selectedConversationId, setSelectedConversationId] = useState<string | undefined>(undefined);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleConversationSelect = (conversationId: string) => {
    setSelectedConversationId(conversationId);
  };

  const handleNewConversation = () => {
    setSelectedConversationId(undefined);
  };

  const handleConversationCreated = (conversationId: string) => {
    setSelectedConversationId(conversationId);
    setRefreshTrigger(prev => prev + 1); // Trigger refresh of conversation list
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold text-gradient">
            Chat with Your Documents
          </h1>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Ask questions about your uploaded documents and get intelligent, context-aware answers powered by advanced AI.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Conversation History Sidebar */}
          <div className="lg:col-span-1">
            <ConversationHistory
              selectedConversationId={selectedConversationId}
              onConversationSelect={handleConversationSelect}
              onNewConversation={handleNewConversation}
              refreshTrigger={refreshTrigger}
            />
          </div>

          {/* Chat Interface */}
          <div className="lg:col-span-3">
            <ChatInterface 
              conversationId={selectedConversationId}
              onConversationCreated={handleConversationCreated}
            />
          </div>
        </div>
      </div>
    </div>
  );
};