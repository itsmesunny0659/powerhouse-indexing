with open('index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Add rk-step-4 in the timeline
target_timeline = '''                                <div id="rk-step-3" class="flex items-center space-x-2 text-slate-400">
                                    <span class="w-2 h-2 rounded-full bg-slate-600"></span>
                                    <span>[Priority 3] Google Caffeine Indexing Buffer Registration</span>
                                </div>'''

new_timeline = '''                                <div id="rk-step-3" class="flex items-center space-x-2 text-slate-400">
                                    <span class="w-2 h-2 rounded-full bg-slate-600"></span>
                                    <span>[Priority 3] Google Caffeine Indexing Buffer Registration</span>
                                </div>
                                <div id="rk-step-4" class="flex items-center space-x-2 text-slate-400">
                                    <span class="w-2 h-2 rounded-full bg-slate-600"></span>
                                    <span>[Priority 4] Top-Tier PBN & Entity Knowledge Graph Assault (DA 99+)</span>
                                </div>'''

if target_timeline in c:
    c = c.replace(target_timeline, new_timeline)
    print('Added rk-step-4 in timeline!')

# 2. Update setStep calls in executeMasterInstantIndex
old_steps_start = '''            setStep('rk-step-0', '[Step 1] Google Indexing API + 12 Service Accounts Rotating...', 'active');
            setStep('rk-step-1', '[Step 2] Summoning Real Googlebot WRS (search.google.com)...', 'waiting');
            setStep('rk-step-2', '[Step 3] Google News Wire & WebSub Hub Dispatch...', 'waiting');
            setStep('rk-step-3', '[Step 4] 200+ Bot Fleet & Global Crawlers Assault...', 'waiting');'''

new_steps_start = '''            setStep('rk-step-0', '[Step 1] Google Indexing API + 12 Service Accounts Rotating...', 'active');
            setStep('rk-step-1', '[Step 2] Summoning Real Googlebot WRS (search.google.com)...', 'waiting');
            setStep('rk-step-2', '[Step 3] Google News Wire & WebSub Hub Dispatch...', 'waiting');
            setStep('rk-step-3', '[Step 4] 200+ Bot Fleet & Global Crawlers Assault...', 'waiting');
            setStep('rk-step-4', '[Step 5] Top-Tier PBN & Entity Knowledge Graph Assault (DA 99+)...', 'waiting');'''

if old_steps_start in c:
    c = c.replace(old_steps_start, new_steps_start)
    print('Added rk-step-4 in steps start!')

old_steps_end = '''                setStep('rk-step-0', '[Step 1] Google Indexing API + 12 Service Accounts Dispatched', 'done');
                setStep('rk-step-1', '[Step 2] Real Googlebot (Chromium WRS) Summoned', 'done');
                setStep('rk-step-2', '[Step 3] Google News Wire & WebSub Hub Verified', 'done');
                setStep('rk-step-3', '[Step 4] 200+ Bot Fleet Assault Active', 'done');'''

new_steps_end = '''                setStep('rk-step-0', '[Step 1] Google Indexing API + 12 Service Accounts Dispatched', 'done');
                setStep('rk-step-1', '[Step 2] Real Googlebot (Chromium WRS) Summoned', 'done');
                setStep('rk-step-2', '[Step 3] Google News Wire & WebSub Hub Verified', 'done');
                setStep('rk-step-3', '[Step 4] 200+ Bot Fleet Assault Active', 'done');
                setStep('rk-step-4', '[Step 5] Top-Tier PBN & Entity Knowledge Graph Assault (DA 99+) Active', 'done');'''

if old_steps_end in c:
    c = c.replace(old_steps_end, new_steps_end)
    print('Added rk-step-4 in steps end!')

# 3. Update status strings to ALL 9 VECTORS
c = c.replace('FIRING ALL 8 VECTORS...', 'FIRING ALL 9 VECTORS (TARGET-DIRECT PBN ACTIVE)...')
c = c.replace('ALL 8 VECTORS COMPLETED', 'ALL 9 VECTORS COMPLETED (TARGET-DIRECT PBN ACTIVE)')
c = c.replace('⚡ 1-CLICK INSTANT INDEX (SUBMIT & FIRE ALL 8 VECTORS) [ENTER ↵]', '⚡ 1-CLICK INSTANT INDEX (SUBMIT & FIRE ALL 9 VECTORS) [ENTER ↵]')

for p in ['index.html', 'public/index.html', 'frontend/index.html']:
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    print('Wrote', p)
