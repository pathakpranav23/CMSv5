document.addEventListener('DOMContentLoaded',function(){
  var toggle=document.querySelector('[data-toggle-sidebar]');
  var sidebar=document.querySelector('.sidebar');
  if(toggle&&sidebar){
    toggle.addEventListener('click',function(){
      sidebar.style.display=sidebar.style.display==='none'?'block':'none'
    })
  }
  var theme=document.querySelector('[data-toggle-theme]');
  if(theme){
    theme.addEventListener('click',function(){
      var d=document.documentElement.style
      var dark=d.getPropertyValue('--bg')==='#0b0f19'
      if(dark){
        d.setProperty('--bg','#ffffff');d.setProperty('--panel','#f7f7f8');d.setProperty('--text','#111827');d.setProperty('--muted','#6b7280');d.setProperty('--primary','#2563eb')
      }else{
        d.setProperty('--bg','#0b0f19');d.setProperty('--panel','#121826');d.setProperty('--text','#e5e7eb');d.setProperty('--muted','#9ca3af');d.setProperty('--primary','#3b82f6')
      }
    })
  }
})
