"use strict";(self.webpackChunkz4d_plugin=self.webpackChunkz4d_plugin||[]).push([[506],{90506:(F,m,r)=>{r.r(m),r.d(m,{ManufacturerModule:()=>D});var f=r(44466),d=r(96749),c=r(88648);class T{constructor(o,n){this.IRCode=o,this.NwkId=n}}var e=r(94650),g=r(5830),Z=r(97185),u=r(54463),p=r(24006),s=r(55017),U=r(10805),v=r(51740);function A(t,o){if(1&t){const n=e.EpF();e._uU(0,"\n              "),e.TgZ(1,"div",13),e._uU(2,"\n                "),e.TgZ(3,"span",14),e._uU(4,"\n                  "),e._UZ(5,"i",15),e._uU(6,"\n                  "),e.TgZ(7,"input",16),e.NdJ("input",function(l){e.CHM(n),e.oxw();const i=e.MAs(21);return e.KtG(i.filterGlobal(l.target.value,"contains"))}),e.ALo(8,"translate"),e.qZA(),e._uU(9,"\n                "),e.qZA(),e._uU(10,"\n              "),e.qZA(),e._uU(11,"\n            ")}2&t&&(e.xp6(7),e.s9C("placeholder",e.lcZ(8,1,"manufacturer.casaia.placeholder")))}function w(t,o){1&t&&(e._uU(0,"\n              "),e.TgZ(1,"tr"),e._uU(2,"\n                "),e.TgZ(3,"th",17),e._uU(4),e.ALo(5,"translate"),e._UZ(6,"p-sortIcon",18),e._uU(7,"\n                "),e.qZA(),e._uU(8,"\n                "),e.TgZ(9,"th",19),e._uU(10),e.ALo(11,"translate"),e._UZ(12,"p-sortIcon",20),e._uU(13,"\n                "),e.qZA(),e._uU(14,"\n                "),e.TgZ(15,"th",21),e._uU(16),e.ALo(17,"translate"),e._UZ(18,"p-sortIcon",22),e._uU(19,"\n                "),e.qZA(),e._uU(20,"\n                "),e.TgZ(21,"th",23),e._uU(22),e.ALo(23,"translate"),e._UZ(24,"p-sortIcon",24),e._uU(25,"\n                "),e.qZA(),e._uU(26,"\n                "),e.TgZ(27,"th",25),e._uU(28),e.ALo(29,"translate"),e._UZ(30,"p-sortIcon",26),e._uU(31,"\n                "),e.qZA(),e._uU(32,"\n              "),e.qZA(),e._uU(33,"\n            ")),2&t&&(e.xp6(4),e.hij("\n                  ",e.lcZ(5,5,"manufacturer.casaia.nwkid"),""),e.xp6(6),e.hij("\n                  ",e.lcZ(11,7,"manufacturer.casaia.name"),""),e.xp6(6),e.hij("\n                  ",e.lcZ(17,9,"manufacturer.casaia.ieee"),""),e.xp6(6),e.hij("\n                  ",e.lcZ(23,11,"manufacturer.casaia.model"),""),e.xp6(6),e.hij("\n                  ",e.lcZ(29,13,"manufacturer.casaia.ircode"),""))}function x(t,o){if(1&t){const n=e.EpF();e._uU(0,"\n                      "),e.TgZ(1,"input",30),e.NdJ("ngModelChange",function(l){e.CHM(n);const i=e.oxw().$implicit;return e.KtG(i.IRCode=l)})("change",function(l){e.CHM(n);const i=e.oxw().$implicit,_=e.oxw();return e.KtG(_.updateIRCode(l,i.NwkId))}),e.qZA(),e._uU(2,"\n                    ")}if(2&t){const n=e.oxw().$implicit;e.xp6(1),e.Q6J("ngModel",n.IRCode)}}function y(t,o){if(1&t){const n=e.EpF();e._uU(0,"\n                      "),e.TgZ(1,"input",30),e.NdJ("ngModelChange",function(l){e.CHM(n);const i=e.oxw().$implicit;return e.KtG(i.IRCode=l)})("change",function(l){e.CHM(n);const i=e.oxw().$implicit,_=e.oxw();return e.KtG(_.updateIRCode(l,i.NwkId))}),e.qZA(),e._uU(2,"\n                    ")}if(2&t){const n=e.oxw().$implicit;e.xp6(1),e.Q6J("ngModel",n.IRCode)}}function I(t,o){if(1&t&&(e._uU(0,"\n              "),e.TgZ(1,"tr"),e._uU(2,"\n                "),e.TgZ(3,"td"),e._uU(4),e.qZA(),e._uU(5,"\n                "),e.TgZ(6,"td"),e._uU(7),e.qZA(),e._uU(8,"\n                "),e.TgZ(9,"td"),e._uU(10),e.qZA(),e._uU(11,"\n                "),e.TgZ(12,"td"),e._uU(13),e.qZA(),e._uU(14,"\n                "),e.TgZ(15,"td",27),e._uU(16,"\n                  "),e.TgZ(17,"p-cellEditor"),e._uU(18,"\n                    "),e.YNc(19,x,3,1,"ng-template",28),e._uU(20,"\n                    "),e.YNc(21,y,3,1,"ng-template",29),e._uU(22,"\n                  "),e.qZA(),e._uU(23,"\n                "),e.qZA()()),2&t){const n=o.$implicit;e.xp6(4),e.hij("\n                  ",n.NwkId,"\n                "),e.xp6(3),e.hij("\n                  ",n.Name,"\n                "),e.xp6(3),e.hij("\n                  ",n.IEEE,"\n                "),e.xp6(3),e.hij("\n                  ",n.Model,"\n                "),e.xp6(2),e.Q6J("pEditableColumn",n.IRCode)}}const b=function(){return["NwkId","Name","IEEE","Model","IRCode"]},M=function(){return[10,25,50]};new c.Yd("CasaiaComponent");let N=(()=>{class t{constructor(n,a,l){this.apiService=n,this.toastr=a,this.translate=l,this.temp=[],this.hasEditing=!1}ngOnInit(){this.getCasaiaDevices()}updateIRCode(n,a){this.hasEditing=!0,this.rows.find(i=>i.NwkId===a).IRCode=n.target.value}updateCasaiaDevices(){const n=[];this.rows.forEach(a=>{n.push(new T(a.IRCode,a.NwkId))}),this.apiService.putCasiaIrcode(n).subscribe(a=>{this.hasEditing=!1,this.getCasaiaDevices(),this.toastr.success(this.translate.instant("api.global.succes.update.notify"))})}getCasaiaDevices(){this.apiService.getCasiaDevices().subscribe(n=>{this.rows=n,this.temp=[...this.rows]})}}return t.\u0275fac=function(n){return new(n||t)(e.Y36(g.s),e.Y36(Z._W),e.Y36(u.sK))},t.\u0275cmp=e.Xpm({type:t,selectors:[["app-manufacturer-casaia"]],decls:36,vars:23,consts:[[1,"row","row-cols-1","row-cols-xxl-2","row-cols-xl-1","g-4"],[1,"col"],[1,"card"],[1,"card-header"],[1,"btn","btn-primary","float-end",3,"disabled","translate","click"],[1,"card-body"],[1,"card-title",3,"innerHTML"],[1,"card-text"],["styleClass","p-datatable-sm","dataKey","NwkId","responsiveLayout","scroll",3,"globalFilterFields","rowHover","showCurrentPageReport","currentPageReportTemplate","rowsPerPageOptions","value","rows","paginator","scrollable"],["dt1",""],["pTemplate","caption"],["pTemplate","header"],["pTemplate","body"],[1,"flex"],[1,"p-input-icon-left","ml-auto"],[1,"pi","pi-search"],["pInputText","","type","text",3,"placeholder","input"],["pSortableColumn","NwkId"],["field","NwkId"],["pSortableColumn","Name"],["field","Name"],["pSortableColumn","IEEE"],["field","IEEE"],["pSortableColumn","Model"],["field","Model"],["pSortableColumn","IRCode",2,"width","8rem"],["field","IRCode"],["pEditableColumnField","IRCode",3,"pEditableColumn"],["pTemplate","input"],["pTemplate","output"],["pInputText","","type","text",3,"ngModel","ngModelChange","change"]],template:function(n,a){1&n&&(e.TgZ(0,"div",0),e._uU(1,"\n  "),e.TgZ(2,"div",1),e._uU(3,"\n    "),e.TgZ(4,"div",2),e._uU(5,"\n      "),e.TgZ(6,"div",3),e._uU(7),e.ALo(8,"translate"),e.TgZ(9,"button",4),e.NdJ("click",function(){return a.updateCasaiaDevices()}),e.ALo(10,"translate"),e.qZA(),e._uU(11,"\n      "),e.qZA(),e._uU(12,"\n      "),e.TgZ(13,"div",5),e._uU(14,"\n        "),e._UZ(15,"h5",6),e.ALo(16,"translate"),e._uU(17,"\n        "),e.TgZ(18,"div",7),e._uU(19,"\n          "),e.TgZ(20,"p-table",8,9),e.ALo(22,"translate"),e._uU(23,"\n            "),e.YNc(24,A,12,3,"ng-template",10),e._uU(25,"\n            "),e.YNc(26,w,34,15,"ng-template",11),e._uU(27,"\n            "),e.YNc(28,I,24,5,"ng-template",12),e._uU(29,"\n          "),e.qZA(),e._uU(30,"\n        "),e.qZA(),e._uU(31,"\n      "),e.qZA(),e._uU(32,"\n    "),e.qZA(),e._uU(33,"\n  "),e.qZA(),e._uU(34,"\n"),e.qZA(),e._uU(35,"\n")),2&n&&(e.xp6(7),e.hij("\n        ",e.lcZ(8,13,"manufacturer.casaia.header"),"\n        "),e.xp6(2),e.s9C("translate",e.lcZ(10,15,"manufacturer.casaia.validate.button")),e.Q6J("disabled",!a.hasEditing),e.xp6(6),e.Q6J("innerHTML",e.lcZ(16,17,"manufacturer.casaia.subtitle"),e.oJD),e.xp6(5),e.s9C("currentPageReportTemplate",e.lcZ(22,19,"TOTAL")),e.Q6J("globalFilterFields",e.DdM(21,b))("rowHover",!0)("showCurrentPageReport",!0)("rowsPerPageOptions",e.DdM(22,M))("value",a.rows)("rows",10)("paginator",!0)("scrollable",!0))},dependencies:[p.Fj,p.JJ,p.On,u.Pi,s.iA,U.jx,s.lQ,s.Wq,s.YL,s.fz,v.o,u.X$]}),t})();class L{}var k=r(54004),C=r(36895),h=r(91835);function R(t,o){if(1&t&&(e._uU(0,"\n              "),e.TgZ(1,"span"),e._uU(2," "),e.TgZ(3,"b"),e._uU(4,"Name"),e.qZA(),e._uU(5),e.TgZ(6,"b"),e._uU(7,"NwkId"),e.qZA(),e._uU(8),e.qZA(),e._uU(9,"\n            ")),2&t){const n=o.item;e.xp6(5),e.hij(" : ",n.ZDeviceName," - "),e.xp6(3),e.hij(" : ",n.Nwkid,"")}}function q(t,o){if(1&t&&(e.TgZ(0,"p",11),e._uU(1),e.ALo(2,"translate"),e.qZA()),2&t){const n=e.oxw();e.xp6(1),e.hij("\n            ",e.lcZ(2,1,"manufacturer.zlinky.".concat(n.deviceSelected.protocole)),"\n          ")}}function P(t,o){1&t&&(e._uU(0,"\n              "),e.TgZ(1,"tr"),e._uU(2,"\n                "),e.TgZ(3,"th"),e._uU(4),e.ALo(5,"translate"),e.qZA(),e._uU(6,"\n                "),e.TgZ(7,"th"),e._uU(8),e.ALo(9,"translate"),e.qZA(),e._uU(10,"\n              "),e.qZA(),e._uU(11,"\n            ")),2&t&&(e.xp6(4),e.hij("\n                  ",e.lcZ(5,2,"manufacturer.zlinky.key"),"\n                "),e.xp6(4),e.hij("\n                  ",e.lcZ(9,4,"manufacturer.zlinky.value"),"\n                "))}function E(t,o){if(1&t&&(e._uU(0,"\n              "),e.TgZ(1,"tr"),e._uU(2,"\n                "),e.TgZ(3,"td"),e._uU(4),e.ALo(5,"translate"),e.qZA(),e._uU(6,"\n                "),e.TgZ(7,"td"),e._uU(8),e.qZA(),e._uU(9,"\n              "),e.qZA()),2&t){const n=o.$implicit;e.xp6(4),e.hij("\n                  ",e.lcZ(5,2,"manufacturer.zlinky.".concat(n.key)),"\n                "),e.xp6(4),e.hij("\n                  ",n.value,"\n                ")}}const j=function(){return[10,25,50]};function J(t,o){if(1&t&&(e.TgZ(0,"p-table",12,13),e.ALo(2,"translate"),e._uU(3,"\n            "),e.YNc(4,P,12,6,"ng-template",14),e._uU(5,"\n            "),e.YNc(6,E,10,4,"ng-template",15),e._uU(7,"\n          "),e.qZA()),2&t){const n=e.oxw();e.s9C("currentPageReportTemplate",e.lcZ(2,8,"TOTAL")),e.Q6J("rowHover",!0)("showCurrentPageReport",!0)("rowsPerPageOptions",e.DdM(10,j))("value",n.deviceSelected.ParametersForDisplay)("rows",10)("paginator",!0)("scrollable",!0)}}new c.Yd("ZlinkyComponent");let O=(()=>{class t{constructor(n,a,l){this.apiService=n,this.toastr=a,this.translate=l}ngOnInit(){this.zlinkys$=this.apiService.getZlinky().pipe((0,k.U)(n=>(n.forEach(a=>{a.protocole="PROTOCOL_LINKY_"+a["PROTOCOL Linky"],a.ParametersForDisplay=[],a.Parameters.forEach(l=>{const i=new L;i.key=Object.keys(l)[0],i.value=Object.values(l)[0],a.ParametersForDisplay.push(i)})}),n)))}getConfiguration(n){this.deviceSelected=n}}return t.\u0275fac=function(n){return new(n||t)(e.Y36(g.s),e.Y36(Z._W),e.Y36(u.sK))},t.\u0275cmp=e.Xpm({type:t,selectors:[["app-manufacturer-zlinky"]],decls:33,vars:17,consts:[[1,"row","row-cols-1","row-cols-xxl-2","row-cols-xl-1","g-4"],[1,"col"],[1,"card"],[1,"card-header"],[1,"card-body"],[1,"card-title",3,"innerHTML"],[1,"card-text"],["bindLabel","ZDeviceName","appendTo","body",1,"w-25",3,"items","multiple","closeOnSelect","searchable","placeholder","change","clear"],["ng-option-tmp",""],["class","mt-3 mb-3 font-weight-bold",4,"ngIf"],["styleClass","p-datatable-sm","responsiveLayout","scroll",3,"rowHover","showCurrentPageReport","currentPageReportTemplate","rowsPerPageOptions","value","rows","paginator","scrollable",4,"ngIf"],[1,"mt-3","mb-3","font-weight-bold"],["styleClass","p-datatable-sm","responsiveLayout","scroll",3,"rowHover","showCurrentPageReport","currentPageReportTemplate","rowsPerPageOptions","value","rows","paginator","scrollable"],["dt1",""],["pTemplate","header"],["pTemplate","body"]],template:function(n,a){1&n&&(e.TgZ(0,"div",0),e._uU(1,"\n  "),e.TgZ(2,"div",1),e._uU(3,"\n    "),e.TgZ(4,"div",2),e._uU(5,"\n      "),e.TgZ(6,"div",3),e._uU(7),e.ALo(8,"translate"),e.qZA(),e._uU(9,"\n      "),e.TgZ(10,"div",4),e._uU(11,"\n        "),e._UZ(12,"h5",5),e.ALo(13,"translate"),e._uU(14,"\n        "),e.TgZ(15,"div",6),e._uU(16,"\n          "),e.TgZ(17,"ng-select",7),e.NdJ("change",function(i){return a.getConfiguration(i)})("clear",function(){return a.deviceSelected=null}),e.ALo(18,"async"),e.ALo(19,"translate"),e._uU(20,"\n            "),e.YNc(21,R,10,2,"ng-template",8),e._uU(22,"\n          "),e.qZA(),e._uU(23,"\n\n          "),e.YNc(24,q,3,3,"p",9),e._uU(25,"\n\n          "),e.YNc(26,J,8,11,"p-table",10),e._uU(27,"\n        "),e.qZA(),e._uU(28,"\n      "),e.qZA(),e._uU(29,"\n    "),e.qZA(),e._uU(30,"\n  "),e.qZA(),e._uU(31,"\n"),e.qZA(),e._uU(32,"\n")),2&n&&(e.xp6(7),e.hij("\n        ",e.lcZ(8,9,"manufacturer.zlinky.header"),"\n      "),e.xp6(5),e.Q6J("innerHTML",e.lcZ(13,11,"manufacturer.zlinky.subtitle"),e.oJD),e.xp6(5),e.s9C("placeholder",e.lcZ(19,15,"manufacturer.zlinky.placeholder")),e.Q6J("items",e.lcZ(18,13,a.zlinkys$))("multiple",!1)("closeOnSelect",!0)("searchable",!0),e.xp6(7),e.Q6J("ngIf",a.deviceSelected),e.xp6(2),e.Q6J("ngIf",a.deviceSelected))},dependencies:[C.O5,h.w9,h.ir,s.iA,U.jx,C.Ov,u.X$]}),t})();const S=[{path:"casaia",component:N,data:{title:(0,c.Kl)("manufacturer.casaia")}},{path:"zlinky",component:O,data:{title:(0,c.Kl)("manufacturer.zlinky")}}];let Y=(()=>{class t{}return t.\u0275fac=function(n){return new(n||t)},t.\u0275mod=e.oAB({type:t}),t.\u0275inj=e.cJS({imports:[d.Bz.forChild(S),d.Bz]}),t})(),D=(()=>{class t{}return t.\u0275fac=function(n){return new(n||t)},t.\u0275mod=e.oAB({type:t}),t.\u0275inj=e.cJS({imports:[Y,f.m]}),t})()}}]);