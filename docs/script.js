document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80, // Account for header
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Bot Status Functionality
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.getElementById('status-text');
    const lastActive = document.getElementById('last-active');
    const runningSince = document.getElementById('running-since');
    const tradingMode = document.getElementById('trading-mode');
    const activePairs = document.getElementById('active-pairs');
    const activityLog = document.getElementById('activity-log');
    const refreshButton = document.getElementById('refresh-status');
    
    // Function to fetch bot status
    const fetchBotStatus = async () => {
        try {
            // This would be replaced with a real API endpoint in production
            // For demo, we'll simulate a response
            
            // In a real implementation, you would do something like:
            // const response = await fetch('https://your-api-endpoint.com/bot/status');
            // const data = await response.json();
            
            // Simulated API response
            const simulateApiCall = () => {
                // Randomly determine if bot is online (80% chance) or offline (20% chance)
                const isOnline = Math.random() < 0.8;
                
                // Current date and time
                const now = new Date();
                const formatDate = (date) => {
                    return date.toLocaleString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                    });
                };
                
                // Determine bot start time (between 1 hour and 7 days ago)
                const startTime = new Date(now);
                startTime.setHours(startTime.getHours() - Math.floor(Math.random() * 168) - 1);
                
                // Recent activity logs
                const activities = [
                    {
                        timestamp: new Date(now - 1000 * 60 * 5), // 5 minutes ago
                        message: "Executed BUY for BTC/USD at $51,324.75",
                        type: "trade"
                    },
                    {
                        timestamp: new Date(now - 1000 * 60 * 15), // 15 minutes ago
                        message: "Market analysis complete: Detected trending market for ETH/USD",
                        type: "info"
                    },
                    {
                        timestamp: new Date(now - 1000 * 60 * 45), // 45 minutes ago
                        message: "Executed SELL for SOL/USD at $123.45",
                        type: "trade"
                    },
                    {
                        timestamp: new Date(now - 1000 * 60 * 120), // 2 hours ago
                        message: "Risk assessment: Portfolio exposure at 12.5%",
                        type: "info"
                    }
                ];
                
                if (!isOnline) {
                    activities.unshift({
                        timestamp: new Date(now - 1000 * 60 * 2), // 2 minutes ago
                        message: "Bot service stopped due to API connection error",
                        type: "error"
                    });
                }
                
                // Trading pairs being monitored
                const pairs = ["BTC/USD", "ETH/USD", "SOL/USD"];
                
                return {
                    status: isOnline ? "online" : "offline",
                    lastActive: isOnline ? now : new Date(now - 1000 * 60 * 2), // 2 minutes ago if offline
                    runningSince: isOnline ? startTime : null,
                    mode: "paper_trading", // or "live_trading" or "backtest"
                    pairs: pairs,
                    activities: activities
                };
            };
            
            const data = simulateApiCall();
            
            // Update status display
            statusDot.className = 'status-dot';
            statusDot.classList.add(data.status);
            
            statusText.textContent = data.status === 'online' ? 'Running' : 'Offline';
            lastActive.textContent = formatTime(data.lastActive);
            
            if (data.runningSince) {
                const duration = calculateDuration(data.runningSince, new Date());
                runningSince.textContent = `${formatTime(data.runningSince)} (${duration})`;
            } else {
                runningSince.textContent = 'Not running';
            }
            
            tradingMode.textContent = formatTradingMode(data.mode);
            activePairs.textContent = data.pairs.join(', ');
            
            // Update activity log
            activityLog.innerHTML = '';
            if (data.activities && data.activities.length > 0) {
                data.activities.forEach(activity => {
                    const activityItem = document.createElement('div');
                    activityItem.className = 'activity-item';
                    
                    const timestamp = document.createElement('span');
                    timestamp.className = 'activity-timestamp';
                    timestamp.textContent = formatTime(activity.timestamp);
                    
                    const message = document.createElement('div');
                    message.className = `activity-message ${activity.type}`;
                    message.textContent = activity.message;
                    
                    activityItem.appendChild(timestamp);
                    activityItem.appendChild(message);
                    activityLog.appendChild(activityItem);
                });
            } else {
                activityLog.innerHTML = '<p>No recent activity to display</p>';
            }
            
        } catch (error) {
            console.error('Error fetching bot status:', error);
            statusDot.className = 'status-dot error';
            statusText.textContent = 'Error checking status';
        }
    };
    
    // Helper functions
    const formatTime = (date) => {
        if (!(date instanceof Date)) {
            date = new Date(date);
        }
        return date.toLocaleString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true
        });
    };
    
    const calculateDuration = (startDate, endDate) => {
        const diffMs = endDate - startDate;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        
        if (diffDays > 0) {
            return `${diffDays}d ${diffHours}h ${diffMinutes}m`;
        } else if (diffHours > 0) {
            return `${diffHours}h ${diffMinutes}m`;
        } else {
            return `${diffMinutes}m`;
        }
    };
    
    const formatTradingMode = (mode) => {
        if (mode === 'paper_trading') return 'Paper Trading';
        if (mode === 'live_trading') return 'Live Trading';
        if (mode === 'backtest') return 'Backtesting';
        return mode;
    };
    
    // Load bot status on page load
    fetchBotStatus();
    
    // Set up refresh button
    if (refreshButton) {
        refreshButton.addEventListener('click', () => {
            statusText.textContent = 'Checking status...';
            statusDot.className = 'status-dot';
            fetchBotStatus();
        });
    }
    
    // Auto refresh status every 60 seconds
    setInterval(fetchBotStatus, 60000);
    
    // Intersection Observer for fade-in animations
    const fadeElements = document.querySelectorAll('.feature-card, .workflow-step, .metric-card, .step-card');
    
    const fadeObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                fadeObserver.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });
    
    fadeElements.forEach(element => {
        element.classList.add('fade-in');
        fadeObserver.observe(element);
    });
    
    // Add animation styles dynamically
    const style = document.createElement('style');
    style.textContent = `
        .fade-in {
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.6s ease-out, transform 0.6s ease-out;
        }
        
        .fade-in.visible {
            opacity: 1;
            transform: translateY(0);
        }
    `;
    document.head.appendChild(style);
    
    // Mobile menu toggle
    const createMobileMenu = () => {
        const nav = document.querySelector('nav');
        const header = document.querySelector('header');
        
        // Create mobile toggle button
        const mobileToggle = document.createElement('button');
        mobileToggle.classList.add('mobile-toggle');
        mobileToggle.innerHTML = '<span></span><span></span><span></span>';
        header.querySelector('.container').appendChild(mobileToggle);
        
        // Add mobile menu toggle styles
        const mobileStyles = document.createElement('style');
        mobileStyles.textContent = `
            @media (max-width: 768px) {
                nav {
                    display: none;
                    width: 100%;
                }
                
                nav.active {
                    display: block;
                }
                
                nav ul {
                    flex-direction: column;
                    align-items: center;
                }
                
                nav ul li {
                    margin: 1rem 0;
                }
                
                .mobile-toggle {
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    width: 30px;
                    height: 22px;
                    background: transparent;
                    border: none;
                    cursor: pointer;
                }
                
                .mobile-toggle span {
                    display: block;
                    width: 100%;
                    height: 3px;
                    background-color: var(--primary-color);
                    border-radius: 3px;
                    transition: all 0.3s;
                }
                
                .mobile-toggle.active span:nth-child(1) {
                    transform: translateY(9px) rotate(45deg);
                }
                
                .mobile-toggle.active span:nth-child(2) {
                    opacity: 0;
                }
                
                .mobile-toggle.active span:nth-child(3) {
                    transform: translateY(-9px) rotate(-45deg);
                }
            }
            
            @media (min-width: 769px) {
                .mobile-toggle {
                    display: none;
                }
            }
        `;
        document.head.appendChild(mobileStyles);
        
        // Add event listener
        mobileToggle.addEventListener('click', () => {
            mobileToggle.classList.toggle('active');
            nav.classList.toggle('active');
        });
        
        // Close menu when clicking a link
        document.querySelectorAll('nav a').forEach(link => {
            link.addEventListener('click', () => {
                mobileToggle.classList.remove('active');
                nav.classList.remove('active');
            });
        });
    };
    
    // Initialize mobile menu
    createMobileMenu();
    
    // Create and add missing images directory and placeholder image
    const createPlaceholderImage = () => {
        // We can't actually create image files in this environment,
        // but we can add a fallback for missing images
        const imgFallback = document.createElement('style');
        imgFallback.textContent = `
            .hero-image img {
                background-color: var(--secondary-color);
                min-height: 300px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.2rem;
                color: white;
                position: relative;
            }
            
            .hero-image img::after {
                content: "Dashboard Preview";
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
            }
        `;
        document.head.appendChild(imgFallback);
    };
    
    // Check if the image exists, if not add fallback
    const dashboardImg = document.querySelector('.hero-image img');
    dashboardImg.onerror = createPlaceholderImage;
});