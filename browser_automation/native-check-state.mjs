// Serialized into the native form. This only reads controls; it never clicks.
export function nativeCheckPreflight(root,data) {
  for(const id of data.ids){
    const button=root.querySelector('[data-field-id="'+id+'"]');
    if(!button||button.disabled||button.classList.contains('ant-btn-loading'))
      throw Error('Check button unavailable or already running');
    const section=root.querySelector('[data-field-id="'+id.replace('-run-button','-section')+'"]');
    const warning=section?.querySelector('[data-field-id$="rerun-warning"]');
    const dirty=!!warning?.getClientRects().length;
    const result=root.querySelector('[data-field-id="'+id.replace('-run-button','-result')+'"]')?.innerText;
    const conclusion=result?.split('\n')[1]?.trim();
    if(!dirty&&conclusion&&conclusion!=='暂无')
      throw Error('Current native result already exists; capture and import it instead of rerunning');
  }
  return {buttons_ready:true};
}
