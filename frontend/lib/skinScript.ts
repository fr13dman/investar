export const SKIN_STORAGE_KEY = "investar-skin";

/** Runs in <head> before first paint so Finviz density tokens apply without a flash. */
export const SKIN_INIT_SCRIPT = `(function(){try{var s=localStorage.getItem("${SKIN_STORAGE_KEY}");document.documentElement.dataset.skin=s==="finviz"?"finviz":"investar"}catch(e){document.documentElement.dataset.skin="investar"}})()`;
