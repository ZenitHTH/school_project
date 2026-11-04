import QtQuick 2.15

Item {
    id: fontContainer
    visible: false

    FontLoader { id: fontNotoRegular; source: "fonts/NotoSansThai-Regular.ttf" }
    FontLoader { id: fontNotoBold; source: "fonts/NotoSansThai-Bold.ttf" }
    FontLoader { id: fontSarabunNew; source: "fonts/THSarabunNew.ttf" }
    FontLoader { id: fontSarabunNewBold; source: "fonts/THSarabunNew-Bold.ttf" }
    FontLoader { id: fontSarabun; source: "fonts/THSarabun.ttf" }
    FontLoader { id: fontTahoma; source: "fonts/Tahoma.ttf" }
    FontLoader { id: fontSukhumvit; source: "fonts/SukhumvitSet.ttc" }
}
