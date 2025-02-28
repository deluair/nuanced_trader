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