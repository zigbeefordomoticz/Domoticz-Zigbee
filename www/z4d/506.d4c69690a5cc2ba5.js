"use strict";(self.webpackChunkz4d_plugin=self.webpackChunkz4d_plugin||[]).push([[506],{90506:(F,m,s)=>{s.r(m),s.d(m,{ManufacturerModule:()=>z});var Z=s(44466),d=s(96749),p=s(88648);class C{constructor(o,n){this.IRCode=o,this.NwkId=n}}var e=s(94650),_=s(5830),g=s(97185),u=s(54463),c=s(69585);const U=["table"];function T(t,o){1&t&&e._uU(0),2&t&&e.hij("\n                ",o.row.NwkId,"\n              ")}function v(t,o){1&t&&e._uU(0),2&t&&e.hij("\n                ",o.row.Name,"\n              ")}function w(t,o){1&t&&e._uU(0),2&t&&e.hij("\n                ",o.row.IEEE,"\n              ")}function y(t,o){1&t&&e._uU(0),2&t&&e.hij("\n                ",o.row.Model,"\n              ")}function A(t,o){if(1&t){const n=e.EpF();e._uU(0,"\n                "),e.TgZ(1,"input",17),e.NdJ("change",function(i){const r=e.CHM(n).row,Q=e.oxw();return e.KtG(Q.updateIRCode(i,r.NwkId))}),e.qZA(),e._uU(2,"\n              ")}if(2&t){const n=o.row;e.xp6(1),e.Q6J("value",n.IRCode)}}const x=function(t,o,n){return{emptyMessage:t,totalMessage:o,selectedMessage:n}};new p.Yd("CasaiaComponent");let b=(()=>{class t{constructor(n,a,i){this.apiService=n,this.toastr=a,this.translate=i,this.temp=[],this.hasEditing=!1}ngOnInit(){this.getCasaiaDevices()}updateIRCode(n,a){this.hasEditing=!0,this.rows.find(l=>l.NwkId===a).IRCode=n.target.value}updateCasaiaDevices(){const n=[];this.rows.forEach(a=>{n.push(new C(a.IRCode,a.NwkId))}),this.apiService.putCasiaIrcode(n).subscribe(a=>{this.hasEditing=!1,this.getCasaiaDevices(),this.toastr.success(this.translate.instant("api.global.succes.update.notify"))})}updateFilter(n){const a=n.target.value.toLowerCase(),i=this.temp.filter(function(l){let r=!1;return l.Model&&(r=-1!==l.Model.toLowerCase().indexOf(a)),!r&&l.NwkId&&(r=-1!==l.NwkId.toLowerCase().indexOf(a)),!r&&l.IEEE&&(r=-1!==l.IEEE.toLowerCase().indexOf(a)),!r&&l.Name&&(r=-1!==l.Name.toLowerCase().indexOf(a)),!r&&l.IRCode&&(r=-1!==l.IRCode.toLowerCase().indexOf(a)),r||!a});this.rows=i,this.table.offset=0}getCasaiaDevices(){this.apiService.getCasiaDevices().subscribe(n=>{this.rows=n,this.temp=[...this.rows]})}}return t.\u0275fac=function(n){return new(n||t)(e.Y36(_.s),e.Y36(g._W),e.Y36(u.sK))},t.\u0275cmp=e.Xpm({type:t,selectors:[["app-manufacturer-casaia"]],viewQuery:function(n,a){if(1&n&&e.Gf(U,5),2&n){let i;e.iGM(i=e.CRH())&&(a.table=i.first)}},decls:65,vars:45,consts:[[1,"row","row-cols-1","row-cols-md-2","g-4"],[1,"col"],[1,"card"],[1,"card-header"],[1,"btn","btn-primary","float-end",3,"disabled","translate","click"],[1,"card-body"],[1,"card-title",3,"innerHTML"],[1,"card-text"],["type","text",3,"placeholder","keyup"],[1,"bootstrap",3,"rows","columnMode","headerHeight","footerHeight","limit","rowHeight","messages"],["table",""],["prop","NwkId",3,"name"],["ngx-datatable-cell-template",""],["prop","Name",3,"name"],["prop","IEEE",3,"name"],["prop","Model",3,"name"],["prop","IRCode",3,"name"],["autofocus","","type","text","size","4","maxlength","4",3,"value","change"]],template:function(n,a){1&n&&(e.TgZ(0,"div",0),e._uU(1,"\n  "),e.TgZ(2,"div",1),e._uU(3,"\n    "),e.TgZ(4,"div",2),e._uU(5,"\n      "),e.TgZ(6,"div",3),e._uU(7),e.ALo(8,"translate"),e.TgZ(9,"button",4),e.NdJ("click",function(){return a.updateCasaiaDevices()}),e.ALo(10,"translate"),e.qZA(),e._uU(11,"\n      "),e.qZA(),e._uU(12,"\n      "),e.TgZ(13,"div",5),e._uU(14,"\n        "),e._UZ(15,"h5",6),e.ALo(16,"translate"),e._uU(17,"\n        "),e.TgZ(18,"div",7),e._uU(19,"\n          "),e.TgZ(20,"input",8),e.NdJ("keyup",function(l){return a.updateFilter(l)}),e.ALo(21,"translate"),e.qZA(),e._uU(22,"\n          "),e.TgZ(23,"ngx-datatable",9,10),e.ALo(25,"translate"),e.ALo(26,"translate"),e.ALo(27,"translate"),e._uU(28,"\n            "),e.TgZ(29,"ngx-datatable-column",11),e.ALo(30,"translate"),e._uU(31,"\n              "),e.YNc(32,T,1,1,"ng-template",12),e._uU(33,"\n            "),e.qZA(),e._uU(34,"\n            "),e.TgZ(35,"ngx-datatable-column",13),e.ALo(36,"translate"),e._uU(37,"\n              "),e.YNc(38,v,1,1,"ng-template",12),e._uU(39,"\n            "),e.qZA(),e._uU(40,"\n            "),e.TgZ(41,"ngx-datatable-column",14),e.ALo(42,"translate"),e._uU(43,"\n              "),e.YNc(44,w,1,1,"ng-template",12),e._uU(45,"\n            "),e.qZA(),e._uU(46,"\n            "),e.TgZ(47,"ngx-datatable-column",15),e.ALo(48,"translate"),e._uU(49,"\n              "),e.YNc(50,y,1,1,"ng-template",12),e._uU(51,"\n            "),e.qZA(),e._uU(52,"\n            "),e.TgZ(53,"ngx-datatable-column",16),e.ALo(54,"translate"),e._uU(55,"\n              "),e.YNc(56,A,3,1,"ng-template",12),e._uU(57,"\n            "),e.qZA(),e._uU(58,"\n          "),e.qZA(),e._uU(59,"\n        "),e.qZA(),e._uU(60,"\n      "),e.qZA(),e._uU(61,"\n    "),e.qZA(),e._uU(62,"\n  "),e.qZA(),e._uU(63,"\n"),e.qZA(),e._uU(64,"\n")),2&n&&(e.xp6(7),e.hij("\n        ",e.lcZ(8,17,"manufacturer.casaia.header"),"\n        "),e.xp6(2),e.s9C("translate",e.lcZ(10,19,"manufacturer.casaia.validate.button")),e.Q6J("disabled",!a.hasEditing),e.xp6(6),e.Q6J("innerHTML",e.lcZ(16,21,"manufacturer.casaia.subtitle"),e.oJD),e.xp6(5),e.s9C("placeholder",e.lcZ(21,23,"manufacturer.casaia.placeholder")),e.xp6(3),e.Q6J("rows",a.rows)("columnMode","force")("headerHeight",40)("footerHeight","auto")("limit",10)("rowHeight","auto")("messages",e.kEZ(41,x,e.lcZ(25,25,"NODATA"),e.lcZ(26,27,"TOTAL"),e.lcZ(27,29,"SELECTED"))),e.xp6(6),e.s9C("name",e.lcZ(30,31,"manufacturer.casaia.nwkid")),e.xp6(6),e.s9C("name",e.lcZ(36,33,"manufacturer.casaia.name")),e.xp6(6),e.s9C("name",e.lcZ(42,35,"manufacturer.casaia.ieee")),e.xp6(6),e.s9C("name",e.lcZ(48,37,"manufacturer.casaia.model")),e.xp6(6),e.s9C("name",e.lcZ(54,39,"manufacturer.casaia.ircode")))},dependencies:[u.Pi,c.nE,c.UC,c.vq,u.X$]}),t})();class k{}var L=s(54004),f=s(36895),h=s(91835),M=s(6957);const N=["table"];function E(t,o){if(1&t&&(e._uU(0,"\n              "),e.TgZ(1,"span",11),e._uU(2,"\n                "),e.TgZ(3,"b"),e._uU(4,"Name"),e.qZA(),e._uU(5),e.TgZ(6,"b"),e._uU(7,"NwkId"),e.qZA(),e._uU(8),e.qZA(),e._uU(9,"\n            ")),2&t){const n=o.item,a=o.searchTerm;e.xp6(1),e.Q6J("ngOptionHighlight",a),e.xp6(4),e.hij(" : ",n.ZDeviceName," - "),e.xp6(3),e.hij(" : ",n.Nwkid,"")}}function I(t,o){if(1&t&&(e.TgZ(0,"p",12),e._uU(1),e.ALo(2,"translate"),e.qZA()),2&t){const n=e.oxw();e.xp6(1),e.hij("\n            ",e.lcZ(2,1,"manufacturer.zlinky.".concat(n.deviceSelected.protocole)),"\n          ")}}function O(t,o){1&t&&(e._uU(0,"\n                "),e.TgZ(1,"span"),e._uU(2),e.ALo(3,"translate"),e.qZA(),e._uU(4,"\n              ")),2&t&&(e.xp6(2),e.Oqu(e.lcZ(3,1,"manufacturer.zlinky.key")))}function H(t,o){1&t&&(e._uU(0),e.ALo(1,"translate")),2&t&&e.hij("\n                ",e.lcZ(1,1,"manufacturer.zlinky.".concat(o.row.key)),"\n              ")}function q(t,o){1&t&&(e._uU(0,"\n                "),e.TgZ(1,"span"),e._uU(2),e.ALo(3,"translate"),e.qZA(),e._uU(4,"\n              ")),2&t&&(e.xp6(2),e.Oqu(e.lcZ(3,1,"manufacturer.zlinky.value")))}function Y(t,o){1&t&&e._uU(0),2&t&&e.hij("\n                ",o.row.value,"\n              ")}const D=function(t,o,n){return{emptyMessage:t,totalMessage:o,selectedMessage:n}};function J(t,o){if(1&t&&(e.TgZ(0,"ngx-datatable",13,14),e.ALo(2,"translate"),e.ALo(3,"translate"),e.ALo(4,"translate"),e._uU(5,"\n            "),e.TgZ(6,"ngx-datatable-column",15),e._uU(7,"\n              "),e.YNc(8,O,5,3,"ng-template",16),e._uU(9,"\n              "),e.YNc(10,H,2,3,"ng-template",17),e._uU(11,"\n            "),e.qZA(),e._uU(12,"\n            "),e.TgZ(13,"ngx-datatable-column",18),e._uU(14,"\n              "),e.YNc(15,q,5,3,"ng-template",16),e._uU(16,"\n              "),e.YNc(17,Y,1,1,"ng-template",17),e._uU(18,"\n            "),e.qZA(),e._uU(19,"\n          "),e.qZA()),2&t){const n=e.oxw();e.Q6J("rows",n.deviceSelected.ParametersForDisplay)("columnMode","force")("headerHeight",40)("footerHeight","auto")("limit",10)("rowHeight","auto")("messages",e.kEZ(13,D,e.lcZ(2,7,"NODATA"),e.lcZ(3,9,"TOTAL"),e.lcZ(4,11,"SELECTED")))}}new p.Yd("ZlinkyComponent");let S=(()=>{class t{constructor(n,a,i){this.apiService=n,this.toastr=a,this.translate=i}ngOnInit(){this.zlinkys$=this.apiService.getZlinky().pipe((0,L.U)(n=>(n.forEach(a=>{a.protocole="PROTOCOL_LINKY_"+a["PROTOCOL Linky"],a.ParametersForDisplay=[],a.Parameters.forEach(i=>{const l=new k;l.key=Object.keys(i)[0],l.value=Object.values(i)[0],a.ParametersForDisplay.push(l)})}),n)))}getConfiguration(n){this.deviceSelected=n}}return t.\u0275fac=function(n){return new(n||t)(e.Y36(_.s),e.Y36(g._W),e.Y36(u.sK))},t.\u0275cmp=e.Xpm({type:t,selectors:[["app-manufacturer-zlinky"]],viewQuery:function(n,a){if(1&n&&e.Gf(N,5),2&n){let i;e.iGM(i=e.CRH())&&(a.table=i.first)}},decls:33,vars:17,consts:[[1,"row","row-cols-1","row-cols-md-2","g-4"],[1,"col"],[1,"card"],[1,"card-header"],[1,"card-body"],[1,"card-title",3,"innerHTML"],[1,"card-text"],["bindLabel","ZDeviceName","appendTo","body",1,"w-25",3,"items","multiple","closeOnSelect","searchable","placeholder","change","clear"],["ng-option-tmp",""],["class","mt-3 mb-3 font-weight-bold",4,"ngIf"],["class","bootstrap",3,"rows","columnMode","headerHeight","footerHeight","limit","rowHeight","messages",4,"ngIf"],[3,"ngOptionHighlight"],[1,"mt-3","mb-3","font-weight-bold"],[1,"bootstrap",3,"rows","columnMode","headerHeight","footerHeight","limit","rowHeight","messages"],["table",""],["prop","key"],["ngx-datatable-header-template",""],["ngx-datatable-cell-template",""],["prop","value"]],template:function(n,a){1&n&&(e.TgZ(0,"div",0),e._uU(1,"\n  "),e.TgZ(2,"div",1),e._uU(3,"\n    "),e.TgZ(4,"div",2),e._uU(5,"\n      "),e.TgZ(6,"div",3),e._uU(7),e.ALo(8,"translate"),e.qZA(),e._uU(9,"\n      "),e.TgZ(10,"div",4),e._uU(11,"\n        "),e._UZ(12,"h5",5),e.ALo(13,"translate"),e._uU(14,"\n        "),e.TgZ(15,"div",6),e._uU(16,"\n          "),e.TgZ(17,"ng-select",7),e.NdJ("change",function(l){return a.getConfiguration(l)})("clear",function(){return a.deviceSelected=null}),e.ALo(18,"async"),e.ALo(19,"translate"),e._uU(20,"\n            "),e.YNc(21,E,10,3,"ng-template",8),e._uU(22,"\n          "),e.qZA(),e._uU(23,"\n\n          "),e.YNc(24,I,3,3,"p",9),e._uU(25,"\n\n          "),e.YNc(26,J,20,17,"ngx-datatable",10),e._uU(27,"\n        "),e.qZA(),e._uU(28,"\n      "),e.qZA(),e._uU(29,"\n    "),e.qZA(),e._uU(30,"\n  "),e.qZA(),e._uU(31,"\n"),e.qZA(),e._uU(32,"\n")),2&n&&(e.xp6(7),e.hij("\n        ",e.lcZ(8,9,"manufacturer.zlinky.header"),"\n      "),e.xp6(5),e.Q6J("innerHTML",e.lcZ(13,11,"manufacturer.zlinky.subtitle"),e.oJD),e.xp6(5),e.s9C("placeholder",e.lcZ(19,15,"manufacturer.zlinky.placeholder")),e.Q6J("items",e.lcZ(18,13,a.zlinkys$))("multiple",!1)("closeOnSelect",!0)("searchable",!0),e.xp6(7),e.Q6J("ngIf",a.deviceSelected),e.xp6(2),e.Q6J("ngIf",a.deviceSelected))},dependencies:[f.O5,h.w9,h.ir,c.nE,c.UC,c.tk,c.vq,M.s,f.Ov,u.X$]}),t})();const R=[{path:"casaia",component:b,data:{title:(0,p.Kl)("manufacturer.casaia")}},{path:"zlinky",component:S,data:{title:(0,p.Kl)("manufacturer.zlinky")}}];let j=(()=>{class t{}return t.\u0275fac=function(n){return new(n||t)},t.\u0275mod=e.oAB({type:t}),t.\u0275inj=e.cJS({imports:[d.Bz.forChild(R),d.Bz]}),t})(),z=(()=>{class t{}return t.\u0275fac=function(n){return new(n||t)},t.\u0275mod=e.oAB({type:t}),t.\u0275inj=e.cJS({imports:[j,Z.m]}),t})()}}]);