"""Exercise the visible app selector rather than the hidden native source field."""
def choose(page,selector,value):
 page.wait_for_function("s=>!!document.querySelector(s)?.nextElementSibling?.classList.contains('hb-choice-trigger')",arg=selector)
 index=page.locator(selector).evaluate("(el,value)=>[...el.options].findIndex(o=>o.value===value)",str(value))
 assert index>=0,selector+': missing option '+str(value)
 page.locator(selector+' + .hb-choice-trigger').click()
 page.locator('#hbChoiceShade [data-index="'+str(index)+'"]').click()
