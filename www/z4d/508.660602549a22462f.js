"use strict";(self.webpackChunkz4d_plugin=self.webpackChunkz4d_plugin||[]).push([[508],{19508:(F,_,l)=>{l.r(_),l.d(_,{GroupModule:()=>H});var c=l(93075),Z=l(44466),m=l(27633),g=l(88648),h=l(62554),U=l(22995),e=l(5e3),v=l(80571),C=l(5830),p=l(27232),x=l(22290),T=l(19513),f=l(94076),d=l(46166),G=l(80399);const b=["table"],A=["content"];function w(o,i){if(1&o){const t=e.EpF();e._uU(0,"\n            "),e.TgZ(1,"i",20),e.NdJ("click",function(){const a=e.CHM(t).row,s=e.oxw();return e.KtG(s.delete(a))}),e.ALo(2,"translate"),e.qZA(),e._uU(3,"\n          ")}2&o&&(e.xp6(1),e.s9C("title",e.lcZ(2,1,"group.create.delete.button")))}function N(o,i){1&o&&e._uU(0),2&o&&e.hij("\n            ",i.row._GroupId,"\n          ")}function E(o,i){if(1&o){const t=e.EpF();e._uU(0,"\n            "),e.TgZ(1,"input",21),e.NdJ("change",function(r){const s=e.CHM(t).row,u=e.oxw();return e.KtG(u.updateValue(r,s._GroupId))}),e.qZA(),e._uU(2,"\n          ")}if(2&o){const t=i.row;e.xp6(1),e.Q6J("value",t.GroupName)}}function I(o,i){if(1&o&&(e._uU(0,"\n                "),e.TgZ(1,"span",24),e._uU(2,"\n                  "),e.TgZ(3,"b"),e._uU(4,"Widget"),e.qZA(),e._uU(5),e.TgZ(6,"b"),e._uU(7,"IEEE"),e.qZA(),e._uU(8),e.TgZ(9,"b"),e._uU(10,"Ep"),e.qZA(),e._uU(11),e.TgZ(12,"b"),e._uU(13,"Id"),e.qZA(),e._uU(14),e.TgZ(15,"b"),e._uU(16),e.qZA(),e._uU(17,"\n                "),e.qZA(),e._uU(18,"\n              ")),2&o){const t=i.item,n=i.searchTerm;e.xp6(1),e.Q6J("ngOptionHighlight",n),e.xp6(4),e.hij(" : ",t.Name," - "),e.xp6(3),e.hij(" : ",t.IEEE," - "),e.xp6(3),e.hij(" : ",t.Ep," -\n                  "),e.xp6(3),e.hij(" : ",t._ID," -\n                  "),e.xp6(2),e.Oqu(t.ZDeviceName)}}function M(o,i){if(1&o){const t=e.EpF();e._uU(0,"\n            "),e.TgZ(1,"ng-select",22),e.NdJ("ngModelChange",function(r){const s=e.CHM(t).row;return e.KtG(s.devicesSelected=r)})("change",function(){e.CHM(t);const r=e.oxw();return e.KtG(r.isFormValid())}),e._uU(2,"\n              "),e.YNc(3,I,19,6,"ng-template",23),e._uU(4,"\n            "),e.qZA(),e._uU(5,"\n          ")}if(2&o){const t=i.row,n=e.oxw();e.xp6(1),e.Q6J("items",n.devices)("multiple",!0)("closeOnSelect",!1)("searchable",!0)("ngModel",t.devicesSelected)}}function k(o,i){if(1&o){const t=e.EpF();e._uU(0,"\n            "),e.TgZ(1,"div",25),e._uU(2,"\n              "),e.TgZ(3,"input",26),e.NdJ("click",function(r){const s=e.CHM(t).row,u=e.oxw();return e.KtG(u.updateCoordinator(r,s))}),e.qZA(),e._uU(4,"\n            "),e.qZA(),e._uU(5,"\n          ")}if(2&o){const t=i.row;e.xp6(3),e.Q6J("checked",t.coordinatorInside)}}function J(o,i){if(1&o){const t=e.EpF();e._uU(0,"\n  "),e.TgZ(1,"div",27),e._uU(2,"\n    "),e._UZ(3,"h4",28),e._uU(4,"\n    "),e.TgZ(5,"button",29),e.NdJ("click",function(){const a=e.CHM(t).$implicit;return e.KtG(a.dismiss("Cross click"))}),e._uU(6,"\n      "),e.TgZ(7,"span",30),e._uU(8,"\xd7"),e.qZA(),e._uU(9,"\n    "),e.qZA(),e._uU(10,"\n  "),e.qZA(),e._uU(11,"\n  "),e._UZ(12,"div",31),e._uU(13,"\n  "),e.TgZ(14,"div",32),e._uU(15,"\n    "),e.TgZ(16,"button",33),e.NdJ("click",function(){const a=e.CHM(t).$implicit;return e.KtG(a.dismiss("cancel"))}),e.qZA(),e._uU(17,"\n  "),e.qZA(),e._uU(18,"\n")}}const y=function(o,i,t){return{emptyMessage:o,totalMessage:i,selectedMessage:t}},S=new g.Yd("GroupComponent"),L=[{path:"",component:(()=>{class o extends U.n{constructor(t,n,r,a,s,u){super(),this.modalService=t,this.apiService=n,this.formBuilder=r,this.translate=a,this.toastr=s,this.headerService=u,this.rows=[],this.rowsTemp=[],this.temp=[],this.hasEditing=!1,this.waiting=!1}ngOnInit(){this.apiService.getZGroupDevicesAvalaible().subscribe(t=>{const n=[];t&&t.length>0&&(t.forEach(r=>{r.WidgetList.forEach(a=>{if("0000"!==r._NwkId){const s=new h.zL;s.Ep=a.Ep,s.IEEE=a.IEEE,s.Name=a.Name,s.ZDeviceName=a.ZDeviceName,s._ID=a._ID,s._NwkId=r._NwkId,n.push(s)}})}),this.devices=[...n],this.getGroups())})}updateValue(t,n){this.hasEditing=!0,this.rows.find(a=>a._GroupId===n).GroupName=t.target.value}updateFilter(t){const n=t.target.value.toLowerCase(),r=this.temp.filter(function(a){let s=!1;return a._GroupId&&(s=-1!==a._GroupId.toLowerCase().indexOf(n)),!s&&a.GroupName&&(s=-1!==a.GroupName.toLowerCase().indexOf(n)),s||!n});this.rows=r,this.table.offset=0}updateDevices(){this.rows.forEach(t=>{t.coordinatorInside&&(t.devicesSelected||(t.devicesSelected=[]),t.devicesSelected.push({Ep:"01",_NwkId:"0000"}))}),this.isFormValid&&this.apiService.putZGroups(this.rows).subscribe(t=>{S.debug(this.rows),this.hasEditing=!1,this.toastr.success(this.translate.instant("api.global.succes.saved.notify")),this.apiService.getRestartNeeded().subscribe(n=>{1===n.RestartNeeded&&(this.headerService.setRestart(!0),this.open(this.content))}),this.waiting=!0,setTimeout(()=>{this.getGroups(),this.waiting=!1},1e3)})}delete(t){const n=this.rows.indexOf(t,0);n>-1&&(this.rows.splice(n,1),this.rows=[...this.rows],this.temp=[...this.rows])}add(){const t=new h.ZA;t.GroupName="",t.coordinatorInside=!1,this.rows.push(t),this.rows=[...this.rows],this.temp=[...this.rows]}updateCoordinator(t,n){n.coordinatorInside=t.currentTarget.checked}open(t){this.modalService.open(t,{ariaLabelledBy:"modal-basic-title"}).result.then(n=>{},n=>{})}isFormValid(){let t=!0;return this.rows.forEach(n=>{n.GroupName&&(n.coordinatorInside||n.devicesSelected&&0!==n.devicesSelected.length)||(t=!1)}),!this.waiting&&t}getGroups(){this.apiService.getZGroups().subscribe(t=>{t&&t.length>0&&(t.forEach(n=>{const r=[];n.coordinatorInside=!1,n.Devices.forEach(a=>{if("0000"===a._NwkId)n.coordinatorInside=!0;else{const s=this.devices.find(u=>u._NwkId===a._NwkId&&u.Ep===a.Ep);null!=s&&r.push(s)}}),n.devicesSelected=r}),this.rows=[...t],this.temp=[...t])})}}return o.\u0275fac=function(t){return new(t||o)(e.Y36(v.FF),e.Y36(C.s),e.Y36(c.qu),e.Y36(p.sK),e.Y36(x._W),e.Y36(T.r))},o.\u0275cmp=e.Xpm({type:o,selectors:[["app-group"]],viewQuery:function(t,n){if(1&t&&(e.Gf(b,5),e.Gf(A,5)),2&t){let r;e.iGM(r=e.CRH())&&(n.table=r.first),e.iGM(r=e.CRH())&&(n.content=r.first)}},features:[e.qOj],decls:71,vars:46,consts:[[1,"card"],[1,"card-header"],["translate","group.create.validate.button",1,"btn","btn-primary","float-right",3,"disabled","click"],[1,"card-body"],[1,"card-title",3,"innerHTML"],[1,"card-text"],[1,"row"],[1,"col-sm"],["type","text",3,"placeholder","keyup"],[1,"col-sm-2"],["translate","group.create.add.button",1,"w-100","btn","btn-primary",3,"click"],[1,"bootstrap",3,"rows","columnMode","headerHeight","footerHeight","limit","rowHeight","messages"],["table",""],[3,"sortable","maxWidth"],["ngx-datatable-cell-template",""],["prop","_GroupId",3,"maxWidth","name"],["prop","GroupName",3,"maxWidth","name"],[3,"name","sortable"],[3,"maxWidth","name","sortable"],["content",""],[1,"fa","fa-trash",2,"cursor","pointer",3,"title","click"],["autofocus","","type","text",3,"value","change"],["bindLabel","Name","placeholder","Choose device","appendTo","body",3,"items","multiple","closeOnSelect","searchable","ngModel","ngModelChange","change"],["ng-option-tmp",""],[3,"ngOptionHighlight"],[1,"form-check"],["type","checkbox",1,"form-check-input",3,"checked","click"],[1,"modal-header"],["id","modal-basic-title","translate","group.reloadplugin.alert.title",1,"modal-title"],["type","button","aria-label","Close",1,"close",3,"click"],["aria-hidden","true"],["translate","group.reloadplugin.alert.subject",1,"modal-body"],[1,"modal-footer"],["type","button","translate","group.reloadplugin.alert.cancel",1,"btn","btn-outline-dark",3,"click"]],template:function(t,n){1&t&&(e.TgZ(0,"div",0),e._uU(1,"\n  "),e.TgZ(2,"div",1),e._uU(3),e.ALo(4,"translate"),e.TgZ(5,"button",2),e.NdJ("click",function(){return n.updateDevices()}),e.qZA(),e._uU(6,"\n  "),e.qZA(),e._uU(7,"\n  "),e.TgZ(8,"div",3),e._uU(9,"\n    "),e._UZ(10,"h5",4),e.ALo(11,"translate"),e._uU(12,"\n    "),e.TgZ(13,"div",5),e._uU(14,"\n      "),e.TgZ(15,"div",6),e._uU(16,"\n        "),e.TgZ(17,"div",7),e._uU(18,"\n          "),e.TgZ(19,"input",8),e.NdJ("keyup",function(a){return n.updateFilter(a)}),e.ALo(20,"translate"),e.qZA(),e._uU(21,"\n        "),e.qZA(),e._uU(22,"\n        "),e.TgZ(23,"div",9),e._uU(24,"\n          "),e.TgZ(25,"button",10),e.NdJ("click",function(){return n.add()}),e.qZA(),e._uU(26,"\n        "),e.qZA(),e._uU(27,"\n      "),e.qZA(),e._uU(28,"\n      "),e.TgZ(29,"ngx-datatable",11,12),e.ALo(31,"translate"),e.ALo(32,"translate"),e.ALo(33,"translate"),e._uU(34,"\n        "),e.TgZ(35,"ngx-datatable-column",13),e._uU(36,"\n          "),e.YNc(37,w,4,3,"ng-template",14),e._uU(38,"\n        "),e.qZA(),e._uU(39,"\n\n        "),e.TgZ(40,"ngx-datatable-column",15),e.ALo(41,"translate"),e._uU(42,"\n          "),e.YNc(43,N,1,1,"ng-template",14),e._uU(44,"\n        "),e.qZA(),e._uU(45,"\n        "),e.TgZ(46,"ngx-datatable-column",16),e.ALo(47,"translate"),e._uU(48,"\n          "),e.YNc(49,E,3,1,"ng-template",14),e._uU(50,"\n        "),e.qZA(),e._uU(51,"\n        "),e.TgZ(52,"ngx-datatable-column",17),e.ALo(53,"translate"),e._uU(54,"\n          "),e.YNc(55,M,6,5,"ng-template",14),e._uU(56,"\n        "),e.qZA(),e._uU(57,"\n        "),e.TgZ(58,"ngx-datatable-column",18),e.ALo(59,"translate"),e._uU(60,"\n          "),e.YNc(61,k,6,1,"ng-template",14),e._uU(62,"\n        "),e.qZA(),e._uU(63,"\n      "),e.qZA(),e._uU(64,"\n    "),e.qZA(),e._uU(65,"\n  "),e.qZA(),e._uU(66,"\n"),e.qZA(),e._uU(67,"\n\n"),e.YNc(68,J,19,0,"ng-template",null,19,e.W1O),e._uU(70,"\n")),2&t&&(e.xp6(3),e.hij("\n    ",e.lcZ(4,22,"group.create.header"),""),e.xp6(2),e.Q6J("disabled",!n.isFormValid()),e.xp6(5),e.Q6J("innerHTML",e.lcZ(11,24,"group.create.subtitle"),e.oJD),e.xp6(9),e.s9C("placeholder",e.lcZ(20,26,"group.create.placeholder")),e.xp6(10),e.Q6J("rows",n.rows)("columnMode","force")("headerHeight",40)("footerHeight","auto")("limit",10)("rowHeight","auto")("messages",e.kEZ(42,y,e.lcZ(31,28,"NODATA"),e.lcZ(32,30,"TOTAL"),e.lcZ(33,32,"SELECTED"))),e.xp6(6),e.Q6J("sortable",!1)("maxWidth",100),e.xp6(5),e.s9C("name",e.lcZ(41,34,"group.create.shortid.column")),e.Q6J("maxWidth",100),e.xp6(6),e.s9C("name",e.lcZ(47,36,"group.create.groupname.column")),e.Q6J("maxWidth",200),e.xp6(6),e.s9C("name",e.lcZ(53,38,"group.create.devices.column")),e.Q6J("sortable",!1),e.xp6(6),e.s9C("name",e.lcZ(59,40,"group.create.coordinator.column")),e.Q6J("maxWidth",150)("sortable",!1))},dependencies:[c.JJ,c.On,f.w9,f.ir,p.Pi,d.nE,d.UC,d.vq,G.s,p.X$]}),o})(),data:{title:(0,g.Kl)("group")}}];let q=(()=>{class o{}return o.\u0275fac=function(t){return new(t||o)},o.\u0275mod=e.oAB({type:o}),o.\u0275inj=e.cJS({imports:[m.Bz.forChild(L),m.Bz]}),o})(),H=(()=>{class o{}return o.\u0275fac=function(t){return new(t||o)},o.\u0275mod=e.oAB({type:o}),o.\u0275inj=e.cJS({imports:[q,Z.m,c.u5]}),o})()}}]);