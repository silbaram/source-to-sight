"""Separately authored source criteria. These are draft references, not human gold answers.

Role names below are independent source roles; candidate IDs and prose are not
used for matching. Identity metadata is copied solely to bind the chosen scope.
Existing reference files are never overwritten by this ledger.
"""
import copy
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
AGENTS = 'src/smolagents/agents.py'
UTILS = 'src/smolagents/utils.py'
MODELS = 'src/smolagents/models.py'
TOOLS = 'src/smolagents/tools.py'
CALLERS = 'src/pluggy/_callers.py'
BLINKER = 'src/blinker/base.py'


def role(key, code, file, line, kind='component', status='confirmed'):
    return dict(key=key, codeNames=[code], file=file, line=line, kind=kind, status=status)


def relation(start, end, kind='invokes', status='confirmed'):
    return dict(fromRole=start, toRole=end, type=kind, status=status)


def behavior(key, kind, owner, file, line, **flags):
    return dict(key=key, kind=kind, role=owner, file=file, line=line, status='confirmed', **flags)


def path(key, kind, *roles):
    return dict(key=key, kind=kind, roles=list(roles))


def save(key, nodes, edges, facts, forbidden, behaviors, paths, forbidden_edges=()):
    target = OUT/'expectations'/f'{key}.json'
    if target.exists():
        return
    graph = json.loads((OUT/'graphs'/f'{key}.json').read_text())
    reference = dict(version=1, caseId=key, review=dict(status='pending',reviewer=None,reviewedAt=None),
                     identity={k:copy.deepcopy(graph[k]) for k in ('layer','language','subject')},
                     profiles=graph['analysis']['profiles'], statuses=['partial'], nodes=nodes, edges=edges,
                     noScenarios=False, requiredFacts=facts, forbiddenClaims=forbidden,
                     forbiddenEdges=list(forbidden_edges), behaviors=behaviors, paths=paths)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(reference,ensure_ascii=False,indent=2)+'\n')


def main():
    save('utility-retry-budget', [
        role('policy','ApiModel.__init__',MODELS,1175), role('controller','Retrying',UTILS,555),
        role('operation','fn',UTILS,557,'boundary','uncertain'), role('classify','is_rate_limit_error',MODELS,1198),
        role('wait','Retrying.delay',UTILS,593,'state')], [
        relation('policy','controller','depends-on'),relation('controller','operation','dispatches'),
        relation('controller','classify','dispatches'),relation('controller','wait','writes'),
        relation('controller','controller','transitions')], [
        'Only positive attempt limits are in scope. N is total attempts, at most N−1 retries; the bare controller defaults to one attempt.',
        'ApiModel retry=True configures total 3 attempts, at most 2 retries; False means total 1.',
        'ApiModel supplies a string-based predicate; 429/rate limit text is not validated HTTP status.',
        'Success returns immediately. Unapproved retry or final failed attempt reraises before backoff/sleep; reraise=False also raises here.',
        'Delay is multiplied before the first sleep. Positive initial wait is not itself the first delay; zero wait remains zero.',
        'Predicate/logging failures, nonpositive budgets and iteration errors after a returned generator are excluded; actual function effects remain unresolved.'
    ], ['3 attempts means 3 retries', 'retry=False returns None on failure', 'The first ApiModel sleep is always exactly 60 seconds',
        'Every BaseException is automatically retried', 'A returned generator is fully consumed inside Retrying', 'Retries undo prior side effects'], [
        behavior('total-budget','rule','controller',UTILS,555,numeric=True),
        behavior('configured-budget','rule','policy',MODELS,1175,numeric=True),
        behavior('wait-update','transition','wait',UTILS,593),
        behavior('retry-guard','step','wait',UTILS,605,branch='retry',condition=True,scenarioKind='retry'),
        behavior('terminal-error','step','controller',UTILS,576,branch='stop',condition=True,scenarioKind='error')], [
        path('success-return','typical','operation','controller'),
        path('allowed-retry','retry','controller','classify','wait','controller','operation'),
        path('failure-stop','error','controller')], [relation('policy','operation')])

    save('plugin-wrapper-unwind', [
        role('request','HookCaller.__call__','src/pluggy/_hooks.py',540),role('runner','_multicall',CALLERS,98),
        role('wrapper','hook_impl.function (wrapper)',CALLERS,113,'boundary','uncertain'),
        role('implementation','hook_impl.function',CALLERS,126,'boundary','uncertain'),role('unwind','teardowns',CALLERS,124,'state')], [
        relation('request','runner'),relation('runner','wrapper','dispatches'),
        relation('runner','unwind','writes'),relation('runner','implementation','dispatches')], [
        'Nonhistoric, default executor, new-style wrappers only; concrete plugin order is not resolved.',
        'HookCaller reads firstresult and passes a copy of implementations; _multicall traverses the supplied list in reverse.',
        'Only wrappers advanced to first yield enter teardowns. Entered wrappers resume in reverse teardown order.',
        'firstresult stops ordinary iteration at a non-None value, including false/zero; entered wrappers still unwind.',
        'Exception uses throw, success uses send. StopIteration from a wrapper supplies a result and clears the pending exception.',
        'After unwind a remaining exception is raised, otherwise the final potentially replaced result is returned.'
    ], ['All registered implementations always run','firstresult only stops at a truthy result','firstresult skips wrapper cleanup',
        'The original exception always survives wrappers','Plugin file order defines total execution order'], [
        behavior('short-circuit','rule','runner',CALLERS,129,numeric=False),
        behavior('wrapper-protocol','rule','unwind',CALLERS,144,numeric=False),
        behavior('entered-stack','transition','unwind',CALLERS,124),
        behavior('exception-clear','transition','runner',CALLERS,164),
        behavior('short-circuit-step','step','runner',CALLERS,129,branch='alternate',condition=True,scenarioKind='lifecycle'),
        behavior('error-unwind','step','wrapper',CALLERS,144,branch='error',scenarioKind='error')], [
        path('normal-unwind','lifecycle','request','wrapper','unwind','implementation','runner','wrapper','runner'),
        path('error-unwind','error','runner','wrapper','runner')], [relation('implementation','wrapper')])

    save('library-resize-callbacks', [
        role('api','Cache.Resize','lru.go',194),role('resize','simplelru.LRU.Resize','simplelru/lru.go',157),
        role('remove','removeOldest / removeElement','simplelru/lru.go',178),
        role('buffer','Cache.evictedKeys / evictedVals','lru.go',191,'state'),role('notify','onEvictedCB','lru.go',197,'boundary','uncertain')], [
        relation('api','resize'),relation('resize','remove'),relation('remove','buffer','writes'),relation('api','notify','dispatches')], [
        'Scope includes a successfully constructed cache and nonnegative new size; negative resize is excluded.',
        'Removal count is max(current length − requested size, 0). Remove oldest that many times, then set capacity.',
        'Internal eviction callback records keys/values under lock; public Resize detaches lists, initializes new buffers and unlocks.',
        'User callbacks run outside the lock only if configured and eviction count is positive. Growth without eviction sends no notifications.',
        'A propagated synchronous callback panic skips later callbacks, with already-applied cache updates remaining.',
        'Callback internals, other goroutine order and unconditional lock release after internal failure are not guaranteed.'
    ], ['Resize always evicts at least one item','Callback executes while the cache lock is held','Callback panic rolls back the resize',
        'All callbacks run even if one panics','Negative capacity has the same count contract as a nonnegative capacity'], [
        behavior('count','rule','resize','simplelru/lru.go',157,numeric=True),
        behavior('notify-release','rule','api','lru.go',194,numeric=False),
        behavior('buffer-lifetime','transition','buffer','lru.go',192),
        behavior('new-capacity','transition','resize','simplelru/lru.go',164),
        behavior('notify-condition','step','notify','lru.go',197,condition=True,execution='sequential',scenarioKind='typical'),
        behavior('callback-failure','step','api','lru.go',197,condition=True,branch='error',scenarioKind='error')], [
        path('release-before-notify','typical','api','remove','buffer','api','notify','api'),
        path('growth','alternate','resize','api'),path('callback-error','error','notify','api')])

    save('agent-parallel-tools', [
        role('entry','MultiStepAgent.run',AGENTS,468),role('loop','MultiStepAgent._run_stream',AGENTS,545),
        role('decision','ToolCallingAgent._step_stream',AGENTS,1336),role('model','model.generate',AGENTS,1309,'boundary','uncertain'),
        role('group','ToolCallingAgent.process_tool_calls',AGENTS,1426),role('execute','ToolCallingAgent.execute_tool_call',AGENTS,1486),
        role('tool','Tool.__call__',TOOLS,246),role('implementation','Tool.forward',TOOLS,246,'boundary','uncertain'),
        role('observations','memory_step.observations',AGENTS,1438,'state'),role('fallback','MultiStepAgent._handle_max_steps_reached',AGENTS,627)], [
        relation('entry','loop'),relation('loop','decision'),relation('decision','model'),relation('decision','group'),
        relation('group','execute'),relation('execute','tool'),relation('tool','implementation'),
        relation('group','observations','writes'),relation('loop','loop','transitions'),relation('loop','fallback')], [
        'Positive per-run max_steps overrides the configured default; constructor default is 20. Steps are not tool calls.',
        'Nonstreaming, unique IDs, ordinary tools inheriting Tool.__call__, text observations and normal callbacks only.',
        'One call is direct; multiple calls are submitted to the executor. Completion order need not equal submission order.',
        'Normal complete consumption records calls and observations sorted by call ID, separate from completion order.',
        'Tool.__call__ checks initialization then transforms inputs, calls forward and transforms outputs; concrete tool internals unresolved.',
        'A future-result failure skips final group observation assembly; earlier side effects need not be rolled back or fully recorded.',
        'AgentGenerationError is reraised; other AgentError is recorded and a later budgeted decision can follow, without guaranteeing the same tool retry.',
        'The finally records the step and increments its number. No final answer at the positive limit invokes the fallback.'
    ], ['Every tool starts simultaneously','Output order proves execution order','async or threads imply a guaranteed worker order',
        'Tool failure rolls back the whole batch','Every successful tool output is always recorded after a batch failure',
        'A generation error automatically retries the model','max_steps counts tool invocations','Agent error always retries the same tool'], [
        behavior('effective-limit','rule','entry',AGENTS,468,numeric=True),
        behavior('completion-order','rule','group',AGENTS,1431,numeric=False),
        behavior('parallel-group','step','group',AGENTS,1426,execution='parallel',condition=True,scenarioKind='typical'),
        behavior('parallel-worker','step','execute',AGENTS,1430,execution='parallel',scenarioKind='typical'),
        behavior('join-record','step','observations',AGENTS,1438,execution='sequential',condition=True,scenarioKind='typical'),
        behavior('observations-state','transition','observations',AGENTS,1439),
        behavior('step-count-state','transition','loop',AGENTS,604),
        behavior('failed-batch','step','group',AGENTS,1432,branch='error',execution='parallel',scenarioKind='error'),
        behavior('generation-stop','step','loop',AGENTS,596,branch='stop',scenarioKind='error')], [
        path('group-join','typical','entry','loop','decision','group','execute','tool','observations','loop'),
        path('recoverable-error','error','group','loop','fallback'),path('fatal-generation','error','decision','loop')], [
        relation('observations','implementation'),relation('model','implementation')])

    save('event-async-lifecycle', [
        role('context','Signal.connected_to',BLINKER,184),role('connect','Signal.connect',BLINKER,128),
        role('send','Signal.send_async',BLINKER,292),role('selection','Signal.receivers_for',BLINKER,343),
        role('adapter','_sync_wrapper',BLINKER,297,'boundary','uncertain'),role('receiver','receiver',BLINKER,299,'boundary','uncertain'),
        role('disconnect','Signal.disconnect',BLINKER,385)], [
        relation('context','connect'),relation('send','selection'),relation('send','adapter','dispatches'),
        relation('send','receiver','dispatches'),relation('context','disconnect')], [
        'The newly connected receiver has no previous registrations; nonnested context with normal bookkeeping.',
        'connected_to connects weak=False, yields to caller code, then disconnects in finally. It does not itself invoke send_async.',
        'Muted async send returns an empty list before selection. Default receiver order is unspecified.',
        'Each receiver is awaited one at a time; this loop does not schedule all receivers in parallel.',
        'Synchronous receiver requires _sync_wrapper; absence raises RuntimeError, otherwise wrapper result is awaited.',
        'Receiver/adapter errors propagate and skip remaining recipients and final normal return. Prior effects remain.',
        'Finally disconnect uses default ANY, not a saved prior-registration restore.'
    ], ['async send runs receivers concurrently','Receiver registration order determines call order','connect directly invokes send_async',
        'All receivers run despite a failure','Errors replay the event later','connected_to restores all earlier registrations'], [
        behavior('await-loop','rule','send',BLINKER,299,numeric=False),
        behavior('adapter-required','rule','send',BLINKER,295,numeric=False),
        behavior('registration-acquired','transition','connect',BLINKER,184),
        behavior('registration-released','transition','disconnect',BLINKER,189),
        behavior('order-unspecified','step','receiver',BLINKER,299,execution='unordered',condition=True,scenarioKind='lifecycle'),
        behavior('error-cleanup','step','disconnect',BLINKER,189,branch='stop',scenarioKind='error'),
        behavior('muted','step','send',BLINKER,287,branch='stop',condition=True,scenarioKind='alternate')], [
        path('scoped-send','lifecycle','connect','send','selection','receiver','send','disconnect'),
        path('failure-cleanup','error','send','disconnect')], [relation('context','send'),relation('connect','receiver')])

    save('web-routing-fallbacks', [
        role('dispatch','Router.ServeHTTP','router.go',471),role('lookup','node.getValue','tree.go',326),
        role('handler','Handle','router.go',473,'boundary','uncertain'),role('redirect','http.Redirect','router.go',493,'boundary','uncertain'),
        role('allowed','Router.allowed','router.go',432),role('error','http.Error / http.NotFound','router.go',527,'boundary','uncertain')], [
        relation('dispatch','lookup'),relation('dispatch','handler','dispatches'),relation('dispatch','redirect'),
        relation('dispatch','allowed'),relation('dispatch','error')], [
        'Fixed-path correction and custom fallback/panic handlers excluded; request path is not server-wide *.',
        'Matching handler runs first; normal return skips fallbacks.',
        'Trailing slash correction requires method tree, missing handler, non-CONNECT, path not /, tsr and enabled setting.',
        'GET correction uses 301, other methods 308; returns before later OPTIONS/error branches.',
        'Automatic OPTIONS with nonempty allow sets Allow and returns; otherwise this branch can fall through to 404.',
        'Outside auto-OPTIONS, enabled MethodNotAllowed plus nonempty allow requests default 405 and returns; otherwise last default is 404.',
        'Handler internals and HTTP implementation are outside the checked source boundary; redirect is not an internal handler rerun.'
    ], ['All unmatched requests return 404','All methods redirect with 301','CONNECT always redirects','Missing method tree triggers slash correction',
        'A redirect calls the destination handler in the same request','405 always wins over slash correction'], [
        behavior('redirect-condition','rule','dispatch','router.go',487,numeric=True),
        behavior('method-condition','rule','dispatch','router.go',521,numeric=True),
        behavior('options-condition','rule','allowed','router.go',514,numeric=True),
        behavior('path-change','transition','dispatch','router.go',489),
        behavior('redirect-stop','step','redirect','router.go',494,branch='stop',scenarioKind='alternate'),
        behavior('method-stop','step','error','router.go',527,branch='stop',condition=True,scenarioKind='error')], [
        path('matched','typical','dispatch','handler'),path('redirect','alternate','dispatch','redirect'),
        path('method-error','error','allowed','error'),path('not-found','error','dispatch','error')], [relation('redirect','handler')])
    print('M2 reference candidates prepared; existing references and approvals preserved.')


if __name__ == '__main__':
    main()
