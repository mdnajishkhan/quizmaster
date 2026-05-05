document.addEventListener('DOMContentLoaded', function() {
    // 1. Find the sidebar
    const sidebar = document.querySelector('#nav-sidebar') || 
                    document.querySelector('.sidebar-menu') || 
                    document.querySelector('#side-menu') ||
                    document.querySelector('nav.sidebar') ||
                    document.querySelector('.main-sidebar');
    
    if (!sidebar) return;

    // 2. SMART AUTO-SCROLL: Find the active/current section
    // Look for common Django/Admin theme active classes
    const activeItem = sidebar.querySelector('.current-model') || 
                       sidebar.querySelector('.active') || 
                       sidebar.querySelector('[aria-current="page"]') ||
                       sidebar.querySelector('.selected');

    if (activeItem) {
        // Jump straight to the active item so the user doesn't have to scroll
        activeItem.scrollIntoView({ block: 'center', behavior: 'instant' });
    } else {
        // Fallback: Restore the last manual scroll position
        const savedScrollPos = sessionStorage.getItem('admin_sidebar_scroll');
        if (savedScrollPos) {
            sidebar.scrollTop = parseInt(savedScrollPos, 10);
        }
    }

    // 3. Keep track of manual scrolling
    const saveScroll = () => {
        sessionStorage.setItem('admin_sidebar_scroll', sidebar.scrollTop);
    };

    sidebar.addEventListener('scroll', saveScroll);
    sidebar.addEventListener('mousedown', saveScroll);
    sidebar.addEventListener('click', saveScroll);
    window.addEventListener('beforeunload', saveScroll);
});
