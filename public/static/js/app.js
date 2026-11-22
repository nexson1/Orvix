// Demo-only frontend state. Replace these sample records with Flask API data later.

let tasks = [
 {id:1,name:"Homepage wireframes",project:"Website redesign",priority:"High",due:"Nov 13, 2026",status:"In progress"},
 {id:2,name:"Review user research",project:"Mobile app",priority:"Medium",due:"Nov 14, 2026",status:"Pending"},
 {id:3,name:"Prepare campaign brief",project:"Marketing campaign",priority:"Low",due:"Nov 16, 2026",status:"Completed"}
];
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function toast(message){const el=$("#toast");el.textContent=message;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),2300)}
function showView(name){document.querySelectorAll(".view").forEach(v=>v.classList.toggle("active",v.id===name));document.querySelectorAll(".nav-link").forEach(b=>b.classList.toggle("active",b.dataset.view===name));$("#crumb").textContent=name[0].toUpperCase()+name.slice(1);$("#sidebar").classList.remove("open");window.scrollTo(0, 0);}
function statusClass(s){return s.toLowerCase().replaceAll(" ","-")}
function taskRow(t,withActions=false){return `<tr><td class="task-title">${esc(t.name)}</td><td>${esc(t.project)}</td><td><span class="priority ${t.priority.toLowerCase()}">${esc(t.priority)}</span></td><td>${esc(t.due||"Not set")}</td><td><span class="status ${statusClass(t.status)}">${esc(t.status)}</span></td>${withActions?`<td><button class="row-delete" data-delete-task="${t.id}" aria-label="Delete task">×</button></td>`:""}</tr>`}

function projectRow(p){return `<div class="project-row"><span class="project-symbol ${p.color}">${p.color==="purple"?"✦":p.color==="blue"?"◈":p.color==="green"?"✓":"◎"}</span><div class="project-info"><b>${esc(p.name)}</b><small>${esc(p.status)}</small></div><div class="mini-progress"><i style="width:${p.progress}%"></i></div><span class="percent">${p.progress}%</span></div>`}
function projectCard(p){return `<article class="project-card"><div class="project-card-top"><span class="project-symbol ${p.color}">✦</span><span class="status ${statusClass(p.status)}">${esc(p.status)}</span></div><h3>${esc(p.name)}</h3><p>${esc(p.description||"No description added yet.")}</p><div class="card-progress"><div><span>Progress</span><b>${p.progress}%</b></div><div class="progress"><i style="width:${p.progress}%"></i></div></div></article>`}
document.addEventListener("click",e=>{
 const nav=e.target.closest("[data-view]");if(nav){showView(nav.dataset.view);return}
 const modal=e.target.closest("[data-modal]");if(modal){$("#"+modal.dataset.modal).classList.add("open");return}
 if(e.target.matches("[data-close]"))e.target.closest(".backdrop").classList.remove("open");
 const del=e.target.closest("[data-delete-task]");if(del){tasks=tasks.filter(t=>t.id!==Number(del.dataset.deleteTask));render();toast("Task removed from this demo.");}
});

// ==============================
// PROJECT SEARCH
// ==============================

const projectSearch = $("#projectSearch");
const projectFilter = $("#projectFilter");

function searchProjects() {
    const query = projectSearch.value.toLowerCase().trim();
    const filter = projectFilter.value.toLowerCase();

    document.querySelectorAll(".project-card").forEach(card => {

        const projectText = card.innerText.toLowerCase();

        const statusElement = card.querySelector(".status");
        const projectStatus = statusElement
            ? statusElement.innerText.toLowerCase()
            : "";

        const matchesSearch = projectText.includes(query);

        const matchesFilter =
            filter === "all" || projectStatus === filter;

        card.style.display =
            matchesSearch && matchesFilter ? "" : "none";
    });
}


// ==============================
// TASK SEARCH
// ==============================

const taskSearch = $("#taskSearch");
const taskFilter = $("#taskFilter");

function searchTasks() {
    const query = taskSearch.value.toLowerCase().trim();
    const filter = taskFilter.value.toLowerCase();

    document.querySelectorAll("#tasks tbody tr").forEach(row => {

        const taskText = row.innerText.toLowerCase();

        const statusElement = row.querySelector(".status-badge");
        const taskStatus = statusElement
            ? statusElement.innerText.toLowerCase()
            : "";

        const matchesSearch = taskText.includes(query);

        const matchesFilter =
            filter === "all" || taskStatus === filter;

        row.style.display =
            matchesSearch && matchesFilter ? "" : "none";
    });
}


// Listen for project searches
projectSearch.addEventListener("input", searchProjects);
projectFilter.addEventListener("change", searchProjects);


// Listen for task searches
taskSearch.addEventListener("input", searchTasks);
taskFilter.addEventListener("change", searchTasks);

// ==============================
// GLOBAL SEARCH - FLASK API
// ==============================

const globalSearch = $("#globalSearch");

const globalResults = document.createElement("div");

globalResults.id = "globalResults";

globalResults.style.cssText = `
    position: absolute;
    top: 65px;
    right: 60px;
    width: 320px;
    max-height: 350px;
    overflow-y: auto;
    background: white;
    border: 1px solid #eee;
    border-radius: 12px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.10);
    z-index: 1000;
    display: none;
`;

$(".top-right").appendChild(globalResults);


let searchTimeout;


// Search Flask database
async function globalSearchResults() {

    const query = globalSearch.value.trim();

    clearTimeout(searchTimeout);

    if (!query) {
        globalResults.style.display = "none";
        return;
    }

    searchTimeout = setTimeout(async () => {

        try {

            globalResults.innerHTML = `
                <p style="padding:15px;color:#888;">
                    Searching...
                </p>
            `;

            globalResults.style.display = "block";

            const response = await fetch(
                `/api/search?q=${encodeURIComponent(query)}`
            );

            if (!response.ok) {
                throw new Error("Search request failed");
            }

            const data = await response.json();

            globalResults.innerHTML = "";

            const results = [
                ...data.projects,
                ...data.tasks
            ];

            if (results.length === 0) {

                globalResults.innerHTML = `
                    <p style="padding:15px;color:#888;">
                        No results found.
                    </p>
                `;

                return;
            }

            results.forEach(result => {

                const item = document.createElement("div");

                item.style.cssText = `
                    padding: 13px 16px;
                    cursor: pointer;
                    border-bottom: 1px solid #f1f1f1;
                `;

                item.innerHTML = `
                    <strong>${esc(result.name)}</strong>
                    <small style="display:block;color:#888;">
                        ${esc(result.type)}
                        ${result.project ? " • " + esc(result.project) : ""}
                    </small>
                `;

                item.addEventListener("click", () => {

                    if (result.type === "Project") {
                        showView("projects");
                    } else {
                        showView("tasks");
                    }

                    globalSearch.value = result.name;

                    globalResults.style.display = "none";

                });

                globalResults.appendChild(item);

            });

        } catch (error) {

            console.error("Search error:", error);

            globalResults.innerHTML = `
                <p style="padding:15px;color:red;">
                    Unable to perform search.
                </p>
            `;

        }

    }, 300);
}


globalSearch.addEventListener("input", globalSearchResults);


// Close dropdown when clicking outside
document.addEventListener("click", e => {

    if (
        !globalSearch.contains(e.target) &&
        !globalResults.contains(e.target)
    ) {
        globalResults.style.display = "none";
    }

});


$("#mobileMenu").addEventListener("click",()=>$("#sidebar").classList.toggle("open"));

