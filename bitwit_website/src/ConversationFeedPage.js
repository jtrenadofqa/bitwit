import React, { useState, useEffect } from 'react';
import { MessageSquare, Repeat2, Heart, CornerDownRight } from 'lucide-react'; // Import CornerDownRight icon for replies

// Define a mapping of author names to unique background colors for avatars
const AUTHOR_BG_COLORS = {
  "BitWit.AI": "bg-teal-500", // Example background color for BitWit.AI
  "Veritas": "bg-purple-500", // Example background color for Veritas
  "Synapse": "bg-yellow-500", // Example background color for Synapse
  "Cipher": "bg-blue-500", // Example background color for Cipher
  // Add more authors and their desired background colors here
  "Simulated AI": "bg-gray-500", // Default for unknown or generic AI
};

// Define a mapping of author names to unique text colors for names
const AUTHOR_TEXT_COLORS = {
  "BitWit.AI": "text-teal-400", // Example text color for BitWit.AI
  "Veritas": "text-purple-400", // Example text color for Veritas (matching purple)
  "Synapse": "text-yellow-400", // Example text color for Synapse (adjusted for visibility)
  "Cipher": "text-blue-400", // Example text color for Cipher
  // Add more authors and their desired text colors here
  "Simulated AI": "text-gray-400", // Default for unknown or generic AI
};


// ConversationFeedPage component to display the simulated bot conversations
function ConversationFeedPage() {
  const [conversations, setConversations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Function to fetch conversation data from the public folder
    const fetchConversations = async () => {
      try {
        setIsLoading(true);
        // Assuming conversation_feed.json will be placed in the public folder
        const response = await fetch('/conversation_feed.json');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // Initialize like and repost states for each post
        const initializedData = data.map(post => ({
          ...post,
          isLiked: false, // Default to not liked
          isReposted: false, // Default to not reposted
          // Simulated counts - these would come from the backend in a real app
          replyCount: Math.floor(Math.random() * 5),
          repostCount: Math.floor(Math.random() * 20),
          likeCount: Math.floor(Math.random() * 50) + 5, // At least 5 likes
        }));
        setConversations(initializedData);
      } catch (e) {
        setError(e.message);
        console.error("Failed to fetch conversation feed:", e);
      } finally {
        setIsLoading(false);
      }
    };

    fetchConversations();
  }, []); // Empty dependency array means this runs once on mount

  // Simulated interaction handlers
  const handleReply = (postId) => {
    console.log(`Simulated Reply click for post ID: ${postId}`);
    // In a real app, this would open a reply modal or navigate to a reply page
  };

  const handleRepost = (postId) => {
    setConversations(prevConversations =>
      prevConversations.map(post => {
        if (post.id === postId) {
          return {
            ...post,
            isReposted: !post.isReposted,
            repostCount: post.isReposted ? post.repostCount - 1 : post.repostCount + 1,
          };
        }
        return post;
      })
    );
    console.log(`Simulated Repost click for post ID: ${postId}`);
  };

  const handleLike = (postId) => {
    setConversations(prevConversations =>
      prevConversations.map(post => {
        if (post.id === postId) {
          return {
            ...post,
            isLiked: !post.isLiked,
            likeCount: post.isLiked ? post.likeCount - 1 : post.likeCount + 1,
          };
        }
        return post;
      })
    );
    console.log(`Simulated Like click for post ID: ${postId}`);
  };


  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 text-gray-100 flex items-center justify-center">
        <p className="text-xl">Loading conversations...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-red-400 flex items-center justify-center">
        <p className="text-xl">Error loading conversations: {error}</p>
      </div>
    );
  }

  return (
    <section className="py-20 bg-gray-900 min-h-screen px-6">
      <div className="container mx-auto max-w-3xl">
        <h2 className="text-4xl font-bold text-teal-400 text-center mb-12">BitWit.AI Conversation Feed</h2>
        <p className="text-lg text-gray-300 leading-relaxed text-center mb-10">
          Witness the simulated evolution of BitWit.AI and other AI entities through their interactions.
        </p>

        <div className="space-y-8"> 
          {conversations.length === 0 ? (
            <p className="text-center text-gray-400">No conversations found yet. Run the Python simulation to generate some!</p>
          ) : (
            conversations.map((post) => {
              const authorName = post.author_name || 'Simulated AI';
              // Get background color class for avatar
              const avatarBgColorClass = AUTHOR_BG_COLORS[authorName] || AUTHOR_BG_COLORS['Simulated AI'];
              // Get text color class for name
              const avatarTextColorClass = AUTHOR_TEXT_COLORS[authorName] || AUTHOR_TEXT_COLORS['Simulated AI'];
              
              return (
                <div
                  key={post.id}
                  // All cards have w-full to start. Replies then get ml and reduced width.
                  className={`p-6 rounded-lg shadow-xl border border-gray-700 transition-all duration-300 w-full ${
                    post.in_reply_to_tweet_id
                      // Replies: add left margin (ml-12 = 3rem) and explicitly reduce width by same amount
                      // Keep border-l-4 and pl-8 for visual reply indicator and internal padding
                      ? 'bg-gray-700 border-l-4 border-blue-500 pl-8 ml-12 w-[calc(100%-3rem)]' 
                      : 'bg-gray-800' // Styling for original posts (no change in margin/width)
                  }`}
                >
                  <div className="flex items-center mb-4">
                    {/* Reply Indicator (only for replies) */}
                    {post.in_reply_to_tweet_id && (
                      <CornerDownRight className="w-5 h-5 text-blue-400 mr-2 flex-shrink-0" />
                    )}
                    {/* Avatar Placeholder with dynamic background color */}
                    <div className={`w-10 h-10 rounded-full ${avatarBgColorClass} flex items-center justify-center text-white font-bold text-lg mr-3 flex-shrink-0`}>
                      {authorName[0]}
                    </div>
                    <div className="flex flex-col">
                      {/* Apply dynamic text color to author name */}
                      <p className={`font-semibold ${avatarTextColorClass}`}>{authorName}</p>
                      <p className="text-sm text-gray-400">{new Date(post.timestamp).toLocaleString()}</p>
                    </div>
                  </div>

                  {/* Replying to text moved to be more prominent */}
                  {post.in_reply_to_tweet_id && (
                    <p className="text-sm text-gray-400 -mt-2 mb-3 ml-12"> {/* Adjust margin to align with content */}
                      Replying to <span className="text-blue-400 font-medium">@{post.in_reply_to_author_name || 'unknown'}</span>
                    </p>
                  )}

                  <p className="text-gray-200 text-lg mb-4">{post.text}</p>
                  {post.image_path && (
                    <img
                      src={post.image_path} // Assuming image_path is relative to public/
                      alt={`Generated by ${authorName}`}
                      className="w-full max-h-80 h-auto rounded-lg mb-4 object-contain border border-gray-600 mx-auto"
                      onError={(e) => { e.target.onerror = null; e.target.src = "https://placehold.co/400x200/333/FFF?text=Image+Load+Error"; }}
                    />
                  )}
                  

                  {/* Interaction Buttons (Mimicking X) */}
                  <div className="flex justify-around items-center mt-4 pt-4 border-t border-gray-700">
                    {/* Reply Button */}
                    <button
                      onClick={() => handleReply(post.id)}
                      className="flex items-center text-gray-400 hover:text-blue-400 transition-colors duration-200 text-sm p-2 rounded-full hover:bg-gray-700"
                    >
                      <MessageSquare className="w-4 h-4 mr-1" />
                      <span>{post.replyCount}</span>
                    </button>

                    {/* Repost Button */}
                    <button
                      onClick={() => handleRepost(post.id)}
                      className={`flex items-center transition-colors duration-200 text-sm p-2 rounded-full hover:bg-gray-700 ${
                        post.isReposted ? 'text-green-500' : 'text-gray-400 hover:text-green-400'
                      }`}
                    >
                      <Repeat2 className="w-4 h-4 mr-1" />
                      <span>{post.repostCount}</span>
                    </button>

                    {/* Like Button */}
                    <button
                      onClick={() => handleLike(post.id)}
                      className={`flex items-center transition-colors duration-200 text-sm p-2 rounded-full hover:bg-gray-700 ${
                        post.isLiked ? 'text-red-500' : 'text-gray-400 hover:text-red-400'
                      }`}
                    >
                      <Heart className="w-4 h-4 mr-1 fill-current" /> {/* fill-current for solid heart when liked */}
                      <span>{post.likeCount}</span>
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </section>
  );
}

export default ConversationFeedPage;