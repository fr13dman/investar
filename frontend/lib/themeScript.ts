export const THEME_STORAGE_KEY = "investar-theme";
export const DARK_QUERY = "(prefers-color-scheme: dark)";

/** Runs in <head> before first paint so the server HTML never flashes the wrong theme. */
export const THEME_INIT_SCRIPT = `(function(){try{var p=localStorage.getItem("${THEME_STORAGE_KEY}");var d=p==="dark"||(p!=="light"&&window.matchMedia("${DARK_QUERY}").matches);var r=document.documentElement;r.classList.toggle("dark",d);r.style.colorScheme=d?"dark":"light"}catch(e){}})()`;
