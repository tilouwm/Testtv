import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import './App.css';
import { Toaster, toast } from 'sonner';
import { 
  Search, 
  Heart, 
  Play, 
  Grid3X3, 
  Filter, 
  Star, 
  Tv, 
  Menu,
  X,
  Settings,
  ChevronRight,
  Volume2,
  VolumeX,
  Maximize,
  Minimize
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// HLS.js integration
let Hls;
if (typeof window !== 'undefined') {
  import('hls.js').then((hlsModule) => {
    Hls = hlsModule.default;
  });
}

function App() {
  // State management
  const [channels, setChannels] = useState([]);
  const [filteredChannels, setFilteredChannels] = useState([]);
  const [categories, setCategories] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [currentFilter, setCurrentFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentChannel, setCurrentChannel] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  
  // Refs
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const userId = 'user-' + Math.random().toString(36).substr(2, 9);

  // Fetch data functions
  const fetchChannels = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/channels`);
      setChannels(response.data);
      setFilteredChannels(response.data);
    } catch (error) {
      console.error('Error fetching channels:', error);
      toast.error('Failed to load channels');
    }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  }, []);

  const fetchFavorites = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/favorites/${userId}`);
      setFavorites(response.data.channel_ids || []);
    } catch (error) {
      console.error('Error fetching favorites:', error);
    }
  }, [userId]);

  const initializeData = useCallback(async () => {
    try {
      await axios.post(`${API}/init-data`);
      toast.success('Data initialized successfully');
    } catch (error) {
      console.error('Error initializing data:', error);
    }
  }, []);

  // Effects
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await initializeData();
      await Promise.all([
        fetchChannels(),
        fetchCategories(),
        fetchFavorites()
      ]);
      setLoading(false);
    };
    loadData();
  }, [initializeData, fetchChannels, fetchCategories, fetchFavorites]);

  // Filter channels based on search, category, and favorites
  useEffect(() => {
    let filtered = channels;

    // Filter by favorites
    if (currentFilter === 'favorites') {
      filtered = filtered.filter(channel => favorites.includes(channel.id));
    }

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(channel => 
        channel.category?.toLowerCase() === selectedCategory.toLowerCase()
      );
    }

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(channel =>
        channel.name.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    setFilteredChannels(filtered);
  }, [channels, favorites, currentFilter, selectedCategory, searchQuery]);

  // Video player functions
  const playChannel = (channel) => {
    if (!videoRef.current || !Hls) return;

    // Clean up previous HLS instance
    if (hlsRef.current) {
      hlsRef.current.destroy();
    }

    setCurrentChannel(channel);
    setIsPlaying(true);

    const video = videoRef.current;
    
    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
      });
      
      hlsRef.current = hls;
      hls.loadSource(channel.stream);
      hls.attachMedia(video);
      
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(console.error);
      });
      
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          console.error('HLS error:', data);
          toast.error(`Failed to load ${channel.name}`);
          setIsPlaying(false);
        }
      });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = channel.stream;
      video.addEventListener('loadedmetadata', () => {
        video.play().catch(console.error);
      });
    } else {
      toast.error('HLS not supported in this browser');
    }
  };

  const stopChannel = () => {
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.src = '';
    }
    setIsPlaying(false);
    setCurrentChannel(null);
    if (document.fullscreenElement) {
      document.exitFullscreen();
    }
  };

  const toggleFavorite = async (channelId) => {
    try {
      await axios.post(`${API}/favorites/${userId}/toggle/${channelId}`);
      await fetchFavorites();
      const channel = channels.find(c => c.id === channelId);
      if (channel) {
        const isFavorite = favorites.includes(channelId);
        toast.success(`${channel.name} ${isFavorite ? 'removed from' : 'added to'} favorites`);
      }
    } catch (error) {
      console.error('Error toggling favorite:', error);
      toast.error('Failed to update favorites');
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      videoRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (videoRef.current) {
      videoRef.current.volume = newVolume;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-purple-500 mx-auto mb-4"></div>
          <p className="text-white text-xl">Loading Haitian TV...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
      <Toaster position="top-right" />
      
      {/* Header */}
      <header className="bg-black/30 backdrop-blur-md border-b border-purple-500/20 sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden text-white hover:text-purple-400 transition-colors"
              >
                <Menu size={24} />
              </button>
              <div className="flex items-center space-x-3">
                <Tv className="text-purple-400" size={32} />
                <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                  Haitian TV
                </h1>
              </div>
            </div>
            
            {/* Search Bar */}
            <div className="hidden md:flex items-center space-x-4 flex-1 max-w-md mx-8">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Search channels..."
                  className="w-full pl-10 pr-4 py-2 bg-white/10 border border-purple-500/30 rounded-lg focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-400/20"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <span className="hidden sm:inline text-sm text-gray-300">
                {filteredChannels.length} channels
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 fixed lg:static inset-y-0 left-0 z-30 w-80 bg-black/40 backdrop-blur-md border-r border-purple-500/20 transition-transform duration-300 ease-in-out`}>
          <div className="p-6">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-xl font-semibold">Filters</h2>
              <button
                onClick={() => setSidebarOpen(false)}
                className="lg:hidden text-gray-400 hover:text-white"
              >
                <X size={20} />
              </button>
            </div>

            {/* Mobile Search */}
            <div className="md:hidden mb-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Search channels..."
                  className="w-full pl-10 pr-4 py-2 bg-white/10 border border-purple-500/30 rounded-lg focus:outline-none focus:border-purple-400"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            {/* Filter Buttons */}
            <div className="space-y-3 mb-8">
              <button
                onClick={() => setCurrentFilter('all')}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                  currentFilter === 'all'
                    ? 'bg-purple-600 text-white shadow-lg'
                    : 'bg-white/5 hover:bg-white/10 text-gray-300'
                }`}
              >
                <Grid3X3 size={20} />
                <span>All Channels</span>
                <div className="ml-auto bg-purple-500/20 px-2 py-1 rounded-full text-xs">
                  {channels.length}
                </div>
              </button>
              
              <button
                onClick={() => setCurrentFilter('favorites')}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                  currentFilter === 'favorites'
                    ? 'bg-purple-600 text-white shadow-lg'
                    : 'bg-white/5 hover:bg-white/10 text-gray-300'
                }`}
              >
                <Heart size={20} />
                <span>Favorites</span>
                <div className="ml-auto bg-purple-500/20 px-2 py-1 rounded-full text-xs">
                  {favorites.length}
                </div>
              </button>
            </div>

            {/* Categories */}
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <Filter size={20} className="mr-2" />
                Categories
              </h3>
              <div className="space-y-2">
                <button
                  onClick={() => setSelectedCategory('all')}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-all ${
                    selectedCategory === 'all'
                      ? 'bg-purple-500/20 text-purple-300'
                      : 'hover:bg-white/5 text-gray-400'
                  }`}
                >
                  All Categories
                </button>
                {categories.map(category => (
                  <button
                    key={category.name}
                    onClick={() => setSelectedCategory(category.name)}
                    className={`w-full text-left px-3 py-2 rounded-lg transition-all flex items-center justify-between ${
                      selectedCategory === category.name
                        ? 'bg-purple-500/20 text-purple-300'
                        : 'hover:bg-white/5 text-gray-400'
                    }`}
                  >
                    <span>{category.name}</span>
                    <span className="text-xs bg-gray-600 px-2 py-1 rounded-full">
                      {category.count}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {/* Current Filter Display */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold mb-2">
              {currentFilter === 'favorites' ? 'Your Favorites' : 
               selectedCategory !== 'all' ? `${selectedCategory} Channels` : 'All Channels'}
            </h2>
            <p className="text-gray-400">
              {filteredChannels.length} channel{filteredChannels.length !== 1 ? 's' : ''} available
            </p>
          </div>

          {/* Channels Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
            {filteredChannels.map(channel => (
              <div
                key={channel.id}
                className="group relative bg-black/30 backdrop-blur-sm rounded-xl p-4 border border-purple-500/20 hover:border-purple-400/50 transition-all duration-300 hover:scale-105 hover:shadow-xl hover:shadow-purple-500/20"
              >
                {/* Channel Logo */}
                <div className="aspect-video bg-black/50 rounded-lg mb-4 overflow-hidden relative">
                  <img
                    src={channel.logo}
                    alt={channel.name}
                    className="w-full h-full object-contain group-hover:scale-110 transition-transform duration-300"
                    onError={(e) => {
                      e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIwIiBoZWlnaHQ9IjgwIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxyZWN0IHdpZHRoPSIxMDAiIGhlaWdodD0iODAiIGZpbGw9IiMzNzM3MzciLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjEyIiBmaWxsPSIjNzc3IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+Tm8gSW1hZ2U8L3RleHQ+PC9zdmc+';
                    }}
                  />
                  
                  {/* Play Overlay */}
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                    <button
                      onClick={() => playChannel(channel)}
                      className="bg-purple-600 hover:bg-purple-700 rounded-full p-3 transform scale-0 group-hover:scale-100 transition-transform duration-300"
                    >
                      <Play size={24} fill="white" />
                    </button>
                  </div>
                </div>

                {/* Channel Info */}
                <div className="space-y-2">
                  <h3 className="font-semibold text-white group-hover:text-purple-300 transition-colors line-clamp-2">
                    {channel.name}
                  </h3>
                  <div className="flex items-center justify-between">
                    <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded-full">
                      {channel.category}
                    </span>
                    <button
                      onClick={() => toggleFavorite(channel.id)}
                      className={`p-1 rounded-full transition-all ${
                        favorites.includes(channel.id)
                          ? 'text-red-400 hover:text-red-300'
                          : 'text-gray-400 hover:text-red-400'
                      }`}
                    >
                      <Heart
                        size={18}
                        fill={favorites.includes(channel.id) ? 'currentColor' : 'none'}
                      />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {filteredChannels.length === 0 && (
            <div className="text-center py-16">
              <Tv size={64} className="mx-auto text-gray-600 mb-4" />
              <h3 className="text-xl font-semibold text-gray-400 mb-2">No channels found</h3>
              <p className="text-gray-500">
                {currentFilter === 'favorites' 
                  ? 'Add some channels to your favorites to see them here'
                  : 'Try adjusting your search or filter criteria'
                }
              </p>
            </div>
          )}
        </main>
      </div>

      {/* Video Player Modal */}
      {isPlaying && currentChannel && (
        <div className="fixed inset-0 bg-black z-50 flex items-center justify-center">
          <div className="relative w-full h-full">
            <video
              ref={videoRef}
              className="w-full h-full object-contain"
              controls
              autoPlay
              muted={isMuted}
            />
            
            {/* Video Controls Overlay */}
            <div className="absolute top-4 left-4 right-4 flex items-center justify-between text-white z-10">
              <div className="flex items-center space-x-4">
                <h3 className="text-xl font-semibold">{currentChannel.name}</h3>
                <span className="bg-purple-600 px-3 py-1 rounded-full text-sm">
                  {currentChannel.category}
                </span>
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={toggleMute}
                  className="p-2 bg-black/50 rounded-full hover:bg-black/70 transition-colors"
                >
                  {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
                </button>
                
                <button
                  onClick={toggleFullscreen}
                  className="p-2 bg-black/50 rounded-full hover:bg-black/70 transition-colors"
                >
                  {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
                </button>
                
                <button
                  onClick={stopChannel}
                  className="p-2 bg-red-600 rounded-full hover:bg-red-700 transition-colors"
                >
                  <X size={20} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}

export default App;